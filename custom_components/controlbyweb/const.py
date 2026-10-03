"""Constants for the ControlByWeb 400 Series integration."""
from __future__ import annotations

import re
from typing import Any

from homeassistant.const import Platform

DOMAIN = "controlbyweb"

CONF_SSL = "ssl"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 80
DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 5  # seconds

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.BUTTON,
]

# Values accepted by state.json?relayN=<value>
RELAY_OFF = 0
RELAY_ON = 1
RELAY_PULSE = 2  # uses the "Pulse Time" configured for the relay on the device

# state.json key prefixes (key = prefix + I/O number)
PREFIX_RELAY = "relay"
PREFIX_DIGITAL_INPUT = "digitalInput"
PREFIX_ONE_WIRE = "oneWireSensor"
PREFIX_ANALOG_INPUT = "analogInput"
PREFIX_ANALOG_OUTPUT = "analogOutput"
PREFIX_REGISTER = "register"
KEY_VIN = "vin"
KEY_SERIAL = "serialNumber"


def indexed_keys(data: dict[str, Any], prefix: str) -> list[tuple[str, int]]:
    """Return [(key, number)] for keys like '<prefix><N>' sorted by N."""
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    found = []
    for key in data:
        if (match := pattern.match(key)):
            found.append((key, int(match.group(1))))
    return sorted(found, key=lambda item: item[1])


def to_float(value: Any) -> float | None:
    """Convert a state.json value to float (device may send strings/empty)."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
