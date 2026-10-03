"""Async client for the ControlByWeb 400 series HTTP/JSON interface.

Reads /state.json and sends commands such as ``state.json?relay1=1``
(0 = off, 1 = on, 2 = pulse), as documented in ControlByWeb's integration manual.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any

import aiohttp


class CBWError(Exception):
    """Base error."""


class CBWAuthError(CBWError):
    """Credentials rejected."""


class CBWConnectionError(CBWError):
    """Device unreachable / timed out."""


class CBWResponseError(CBWError):
    """Device answered, but not like a 400 series module (HTTP error, reset, bad data)."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class CBWClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int = 80,
        username: str | None = None,
        password: str | None = None,
        ssl: bool = False,
        show_units: bool = True,
    ) -> None:
        scheme = "https" if ssl else "http"
        self._base = f"{scheme}://{host}:{port}"
        self._session = session
        self._auth = aiohttp.BasicAuth(username or "none", password) if password else None
        self.show_units = show_units

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
        except aiohttp.ClientConnectorError as err:  # refused / unreachable host
            raise CBWConnectionError(str(err) or type(err).__name__) from err
        except (aiohttp.ServerDisconnectedError, aiohttp.ClientOSError) as err:
            # Device is up but dropped the connection (e.g. a model without state.json)
            raise CBWResponseError(f"Connection closed by device: {err}") from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CBWConnectionError(str(err) or type(err).__name__) from err

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


def create_client(session: aiohttp.ClientSession, data: Mapping[str, Any]) -> CBWClient:
    """Build a client from stored config-entry data."""
    return CBWClient(
        session,
        data["host"],
        data["port"],
        data.get("username"),
        data.get("password"),
        data.get("ssl", False),
        data.get("show_units", True),
    )


async def detect_client(
    session: aiohttp.ClientSession, data: Mapping[str, Any]
) -> tuple[CBWClient, dict[str, Any]]:
    """Connect, preferring showUnits=1; fall back to plain state.json if rejected."""
    client = create_client(session, {**data, "show_units": True})
    try:
        return client, await client.get_state()
    except CBWResponseError as err:
        # A 404 or a dropped connection means "not a 400 series": don't retry.
        if err.status is None or err.status == 404:
            raise
    client = create_client(session, {**data, "show_units": False})
    return client, await client.get_state()
