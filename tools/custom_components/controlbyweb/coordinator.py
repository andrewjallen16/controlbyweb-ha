"""Data update coordinator."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CBWAuthError, CBWError, _BaseClient
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CBWCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the device and sends commands."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: _BaseClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.unique_id}",
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.get_state()
        except CBWAuthError as err:
            raise ConfigEntryAuthFailed from err
        except CBWError as err:
            raise UpdateFailed(f"Error talking to device: {err}") from err

    async def async_send(self, **params: Any) -> None:
        """Send a command, then refresh state immediately."""
        try:
            await self.client.send_command(params)
        except CBWError as err:
            raise HomeAssistantError(f"Command failed: {err}") from err
        await self.async_refresh()
