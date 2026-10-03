"""ControlByWeb 400 Series integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import create_client
from .const import CONF_SSL, PLATFORMS
from .coordinator import CBWCoordinator

type CBWConfigEntry = ConfigEntry[CBWCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: CBWConfigEntry) -> bool:
    ssl = entry.data.get(CONF_SSL, False)
    # Devices ship with a self-signed certificate, so don't verify when using HTTPS.
    session = async_get_clientsession(hass, verify_ssl=not ssl)
    client = create_client(session, entry.data)
    coordinator = CBWCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload_on_update))
    return True


async def _reload_on_update(hass: HomeAssistant, entry: CBWConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: CBWConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
