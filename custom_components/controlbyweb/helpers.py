"""Small shared helpers."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SSL, CONF_VERIFY_SSL


def get_session(hass: HomeAssistant, data: Mapping[str, Any]):
    """HTTP session. Devices ship self-signed certificates, so HTTPS certificate
    checking is off unless the user turns on "Verify certificate"."""
    if data.get(CONF_SSL, False):
        return async_get_clientsession(hass, verify_ssl=data.get(CONF_VERIFY_SSL, False))
    return async_get_clientsession(hass)


def registered_keys(hass: HomeAssistant, entry: ConfigEntry, domain: str) -> set[str]:
    """State keys that already have an entity of `domain` for this device.

    An I/O that was seen once keeps its entity (unavailable while unplugged, e.g. a
    1-Wire probe) instead of disappearing when the device reports 'x.x'.
    """
    prefix = f"{entry.unique_id}_"
    registry = er.async_get(hass)
    return {
        ent.unique_id[len(prefix):]
        for ent in er.async_entries_for_config_entry(registry, entry.entry_id)
        if ent.domain == domain and ent.unique_id and ent.unique_id.startswith(prefix)
    }
