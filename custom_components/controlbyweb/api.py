"""Async client for the ControlByWeb 400 Series HTTP interface."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class CBWError(Exception):
    """Base error."""


class CBWAuthError(CBWError):
    """Credentials rejected."""


class CBWConnectionError(CBWError):
    """Device unreachable or bad response."""


class CBWClient:
    """Talks to /state.json on a 400 Series device."""

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
        self._auth = (
            aiohttp.BasicAuth(username or "", password) if password else None
        )

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            async with asyncio.timeout(10):
                async with self._session.get(
                    f"{self._base}{path}", params=params, auth=self._auth
                ) as resp:
                    if resp.status in (401, 403):
                        raise CBWAuthError("Authentication failed")
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
        except CBWAuthError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CBWConnectionError(str(err)) from err
        except ValueError as err:
            raise CBWError(f"Invalid JSON from device: {err}") from err

    async def get_state(self) -> dict[str, Any]:
        """Fetch the full I/O state."""
        data = await self._request("/state.json")
        if not isinstance(data, dict):
            raise CBWError("Unexpected state.json format")
        return data

    async def send_command(self, params: dict[str, Any]) -> None:
        """Send a control command, e.g. {'relay1': 1}."""
        await self._request("/state.json", params=params)
