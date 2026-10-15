"""Data update coordinator."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CBWAuthError, CBWClient, CBWError
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_USE_DEVICE_NAMES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    build_name_map,
)

_LOGGER = logging.getLogger(__name__)


class CBWCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the device and sends commands."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: CBWClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.unique_id}",
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
            always_update=False,  # only notify entities when the data actually changed
        )
        self.client = client
        self.custom_names: dict[str, str] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.get_state()
        except CBWAuthError as err:
            raise ConfigEntryAuthFailed from err
        except CBWError as err:
            raise UpdateFailed(f"Error talking to device: {err}") from err

    async def async_load_names(self) -> None:
        """Fetch the device's own I/O names (opt-in; read once per setup)."""
        self.custom_names = {}
        if not self.config_entry.options.get(CONF_USE_DEVICE_NAMES):
            return
        try:
            state = await self.client.get_state()
            custom = await self.client.get_custom_state()
        except CBWError as err:
            _LOGGER.warning("Could not read device I/O names, using generic names: %s", err)
            return
        self.custom_names = build_name_map(state, custom)
        if not self.custom_names:
            _LOGGER.info(
                "Device I/O names were not used: no custom names set, or customState.json "
                "did not line up with state.json (diagnostics show both)"
            )

    async def async_send(self, **params: Any) -> None:
        """Send a command (parameter order is preserved), then refresh immediately."""
        try:
            await self.client.send_command(params)
        except CBWError as err:
            raise HomeAssistantError(f"Command failed: {err}") from err
        await self.async_refresh()
