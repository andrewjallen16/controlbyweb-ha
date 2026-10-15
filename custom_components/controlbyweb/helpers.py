"""Small shared helpers."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SSL, CONF_VERIFY_SSL


def get_session(hass: HomeAssistant, data: Mapping[str, Any]):
    """HTTP session. Devices ship self-signed certificates, so HTTPS certificate
    checking is off unless the user turns on "Verify certificate"."""
    if data.get(CONF_SSL, False):
        return async_get_clientsession(hass, verify_ssl=data.get(CONF_VERIFY_SSL, False))
    return async_get_clientsession(hass)
