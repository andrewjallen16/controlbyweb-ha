"""Diagnostics download (passwords and location are redacted)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import CBWConfigEntry
from .api import CBWError
from .const import KEY_SERIAL, describe_state, guess_model

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME, CONF_HOST, KEY_SERIAL, "lat", "long"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CBWConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    custom_state: Any
    try:
        custom_state = await coordinator.client.get_custom_state()
    except CBWError as err:
        custom_state = f"unavailable: {err}"
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
        },
        "summary": describe_state(coordinator.data),
        "guessed_model": guess_model(coordinator.data),
        "state": async_redact_data(coordinator.data, TO_REDACT),
        "custom_state": (
            async_redact_data(custom_state, TO_REDACT)
            if isinstance(custom_state, dict)
            else custom_state
        ),
        "custom_names_in_use": coordinator.custom_names,
    }
