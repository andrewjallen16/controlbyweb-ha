"""Async clients for ControlByWeb devices.

Two protocols are supported:

* ``json`` - 400 series (X-401/404/408/410/420 ...): /state.json, commands such as
  ``state.json?relay1=1`` (0=off, 1=on, 2=pulse).
* ``xml``  - older WebRelay units (X-WR-1R12 ...): /state.xml with tags like
  <relaystate>/<inputstate>, commands such as ``state.xml?relayState=1``.

The XML client normalises its data to the same key names the JSON client uses
(relay1, digitalInput1, ...) so the Home Assistant entities are protocol-agnostic.
"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping
from typing import Any

import aiohttp

PROTO_JSON = "json"
PROTO_XML = "xml"


class CBWError(Exception):
    """Base error."""


class CBWAuthError(CBWError):
    """Credentials rejected."""


class CBWConnectionError(CBWError):
    """Device unreachable / timed out."""


class CBWResponseError(CBWError):
    """Device answered, but with an HTTP error or unusable data."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class _BaseClient:
    protocol: str = ""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int = 80,
        username: str | None = None,
        password: str | None = None,
        ssl: bool = False,
    ) -> None:
        scheme = "https" if ssl else "http"
        self._base = f"{scheme}://{host}:{port}"
        self._session = session
        self._auth = aiohttp.BasicAuth(username or "none", password) if password else None

    async def _get(self, path: str, params: Mapping[str, Any] | None = None) -> str:
        query = {k: str(v) for k, v in params.items()} if params else None
        try:
            async with asyncio.timeout(10):
                async with self._session.get(
                    f"{self._base}{path}", params=query, auth=self._auth
                ) as resp:
                    if resp.status in (401, 403):
                        raise CBWAuthError("Authentication failed")
                    if resp.status >= 400:
                        raise CBWResponseError(f"HTTP {resp.status}", resp.status)
                    return await resp.text()
        except CBWError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CBWConnectionError(str(err) or type(err).__name__) from err

    async def get_state(self) -> dict[str, Any]:
        raise NotImplementedError

    async def send_command(self, params: Mapping[str, Any]) -> None:
        raise NotImplementedError


class CBWJsonClient(_BaseClient):
    """400 series: /state.json."""

    protocol = PROTO_JSON

    def __init__(self, *args: Any, show_units: bool = True, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.show_units = show_units

    async def get_state(self) -> dict[str, Any]:
        # showUnits=1 makes 1-Wire sensors report e.g. "77.3 F" instead of "77.3"
        text = await self._get("/state.json", {"showUnits": 1} if self.show_units else None)
        try:
            data = json.loads(text)
        except ValueError as err:
            raise CBWResponseError(f"state.json is not valid JSON: {err}") from err
        if not isinstance(data, dict):
            raise CBWResponseError("Unexpected state.json format")
        return data

    async def send_command(self, params: Mapping[str, Any]) -> None:
        await self._get("/state.json", params)


_TAG_RE = re.compile(r"<([A-Za-z][A-Za-z0-9_]*)>([^<]*)</\1>")
_RELAY_TAG = re.compile(r"relay(\d*)state")
_INPUT_TAG = re.compile(r"input(\d*)state")


class CBWXmlClient(_BaseClient):
    """Older WebRelay units: /state.xml (relaystate, inputstate, rebootstate...)."""

    protocol = PROTO_XML

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # relay number -> command parameter name, learned from the tags seen
        # e.g. {1: "relayState"} (single relay) or {1: "relay1State", 2: ...}
        self._relay_param: dict[int, str] = {}

    async def get_state(self) -> dict[str, Any]:
        text = await self._get("/state.xml")
        raw = {k: v.strip() for k, v in _TAG_RE.findall(text) if k.lower() != "datavalues"}
        if not raw:
            raise CBWResponseError("state.xml contained no data")
        return self._normalise(raw)

    def _normalise(self, raw: Mapping[str, str]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in raw.items():
            low = key.lower()
            if m := _RELAY_TAG.fullmatch(low):
                n = int(m.group(1) or 1)
                self._relay_param[n] = f"relay{m.group(1)}State"
                out[f"relay{n}"] = value
            elif m := _INPUT_TAG.fullmatch(low):
                out[f"digitalInput{int(m.group(1) or 1)}"] = value
            elif low == "rebootstate":
                out["rebootState"] = value
            elif low == "totalreboots":
                out["totalReboots"] = value
            else:
                out[key] = value  # 400-series-style tags pass straight through
        return out

    async def send_command(self, params: Mapping[str, Any]) -> None:
        query: dict[str, Any] = {}
        for key, value in params.items():
            m = re.fullmatch(r"relay(\d+)", key)
            if m and int(m.group(1)) in self._relay_param:
                query[self._relay_param[int(m.group(1))]] = value
            else:
                query[key] = value
        if self._relay_param:
            query["noReply"] = 1  # we refresh state ourselves afterwards
        await self._get("/state.xml", query)


def create_client(session: aiohttp.ClientSession, data: Mapping[str, Any]) -> _BaseClient:
    """Build the right client from stored config-entry data."""
    kwargs = {
        "host": data["host"],
        "port": data["port"],
        "username": data.get("username"),
        "password": data.get("password"),
        "ssl": data.get("ssl", False),
    }
    if data.get("protocol") == PROTO_XML:
        return CBWXmlClient(session, **kwargs)
    return CBWJsonClient(session, **kwargs, show_units=data.get("show_units", True))


async def detect_client(
    session: aiohttp.ClientSession, data: Mapping[str, Any]
) -> tuple[_BaseClient, dict[str, Any]]:
    """Work out which protocol a device speaks. Returns (client, first_state).

    Order: 400-series JSON (with units), JSON without units, legacy XML.
    Unreachable devices and bad credentials fail fast instead of trying all three.
    """
    base = {**data, "protocol": PROTO_JSON}
    candidates: list[_BaseClient] = [
        create_client(session, {**base, "show_units": True}),
    ]
    last: CBWError | None = None
    tried_plain_json = False

    while candidates:
        client = candidates.pop(0)
        try:
            return client, await client.get_state()
        except (CBWAuthError, CBWConnectionError):
            raise
        except CBWError as err:
            last = err
            if isinstance(client, CBWJsonClient) and client.show_units:
                # Only worth retrying without showUnits if the endpoint exists at all
                status = getattr(err, "status", None)
                if status != 404 and not tried_plain_json:
                    tried_plain_json = True
                    candidates.append(create_client(session, {**base, "show_units": False}))
                    continue
                candidates.append(create_client(session, {**data, "protocol": PROTO_XML}))
            elif isinstance(client, CBWJsonClient):
                candidates.append(create_client(session, {**data, "protocol": PROTO_XML}))
    assert last is not None
    raise last
