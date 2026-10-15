"""ControlByWeb 400 series integration."""
from __future__ import annotations

import logging
import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .api import create_client
from .const import CONF_WRITABLE_REGISTERS, PLATFORMS, is_configured, unhandled_keys
from .coordinator import CBWCoordinator
from .helpers import get_session

type CBWConfigEntry = ConfigEntry[CBWCoordinator]

_LOGGER = logging.getLogger(__name__)

_REGISTER_UID = re.compile(r"_register\d+$")
_UNREADABLE_KEY = re.compile(r"^(oneWireSensor|analogInput|analogOutput|register|frequencyInput)\d*$")
CLEANUP_MINOR_VERSION = 2  # entries older than this get the one-time cleanup below


async def async_setup_entry(hass: HomeAssistant, entry: CBWConfigEntry) -> bool:
    client = create_client(get_session(hass, entry.data), entry.data)
    coordinator = CBWCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_load_names()
    if extra := unhandled_keys(coordinator.data):
        _LOGGER.info(
            "state.json contains keys this integration does not use yet: %s. "
            "If one is an I/O you expected, open an issue and attach the diagnostics download.",
            ", ".join(extra),
        )
    entry.runtime_data = coordinator

    if entry.minor_version < CLEANUP_MINOR_VERSION:
        # Older versions created entities for every empty 1-Wire/register slot ("x.x").
        # Remove the ones that are not in use now, once. From here on, an I/O that has
        # been seen keeps its entity and shows as unavailable while unplugged.
        _async_remove_unused_entities(hass, entry, coordinator.data)
        hass.config_entries.async_update_entry(entry, minor_version=CLEANUP_MINOR_VERSION)

    _async_remove_stale_register_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload_on_update))
    return True


@callback
def _async_remove_unused_entities(hass: HomeAssistant, entry: CBWConfigEntry, data: dict) -> None:
    registry = er.async_get(hass)
    prefix = f"{entry.unique_id}_"
    for ent in er.async_entries_for_config_entry(registry, entry.entry_id):
        uid = ent.unique_id or ""
        if ent.domain not in ("sensor", "number") or not uid.startswith(prefix):
            continue
        key = uid[len(prefix):]
        if _UNREADABLE_KEY.match(key) and not is_configured(data.get(key)):
            registry.async_remove(ent.entity_id)


@callback
def _async_remove_stale_register_entities(hass: HomeAssistant, entry: CBWConfigEntry) -> None:
    """Registers are sensors by default and numbers when writing is enabled;
    drop the other kind so toggling the option doesn't leave dead entities."""
    stale_domain = "sensor" if entry.options.get(CONF_WRITABLE_REGISTERS) else "number"
    registry = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(registry, entry.entry_id):
        if ent.domain == stale_domain and _REGISTER_UID.search(ent.unique_id or ""):
            registry.async_remove(ent.entity_id)


async def _reload_on_update(hass: HomeAssistant, entry: CBWConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: CBWConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
