"""Constants for the ControlByWeb integration."""
from __future__ import annotations

import re
from typing import Any

from homeassistant.const import Platform

DOMAIN = "controlbyweb"

CONF_SSL = "ssl"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ONEWIRE_UNIT = "onewire_unit"
CONF_PROTOCOL = "protocol"  # "json" (400 series) or "xml" (older WebRelay)
CONF_SHOW_UNITS = "show_units"
CONF_MODEL = "model"

DEFAULT_PORT = 80
DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 5  # seconds
MIN_SCAN_INTERVAL = 3  # devices report minRecRefresh = 3
UNIT_NONE = "none"

MODEL_UNSPECIFIED = "Not specified"
MODELS = [
    MODEL_UNSPECIFIED,
    "X-401",
    "X-404",
    "X-408",
    "X-410",
    "X-420",
    "X-WR-1R12",
    "Other 400 series",
    "Other WebRelay",
]

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.BUTTON,
]

# Relay command values: state.json?relayN=<value>
RELAY_OFF = 0
RELAY_ON = 1
RELAY_PULSE = 2  # uses the "Pulse Time" configured for the relay on the device

# Key names (as used in state.json; the XML client normalises to these too)
PREFIX_RELAY = "relay"
PREFIX_DIGITAL_INPUT = "digitalInput"
PREFIX_DIGITAL_IO = "digitalIO"  # X-420: direction is configured on the device
PREFIX_ONE_WIRE = "oneWireSensor"
PREFIX_ANALOG_INPUT = "analogInput"
PREFIX_ANALOG_OUTPUT = "analogOutput"
PREFIX_REGISTER = "register"
PREFIX_ON_TIME = "onTime"
PREFIX_TOTAL_ON_TIME = "totalOnTime"
PREFIX_COUNT = "count"
PREFIX_FREQUENCY = "frequency"
KEY_FREQUENCY_INPUT = "frequencyInput"  # X-420 dedicated frequency input
KEY_VIN = "vin"  # some units report "vin", others "vin1"
KEY_SERIAL = "serialNumber"
KEY_REBOOT_STATE = "rebootState"  # legacy WebRelay auto-reboot mode
KEY_TOTAL_REBOOTS = "totalReboots"

REBOOT_STATES = {
    0: "auto_reboot_off",
    1: "pinging",
    2: "waiting_for_response",
    3: "rebooting",
    4: "waiting_for_boot",
}

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
_NUMBER_RE = re.compile(r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*?)\s*$")

# Units as printed by the device (showUnits=1) -> Home Assistant units
UNIT_MAP = {"F": "\u00b0F", "C": "\u00b0C", "%RH": "%"}


def indexed_keys(data: dict[str, Any], prefix: str) -> list[tuple[str, int]]:
    """Return [(key, number)] for keys like '<prefix><N>' sorted by N."""
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    found = []
    for key in data:
        if match := pattern.match(key):
            found.append((key, int(match.group(1))))
    return sorted(found, key=lambda item: item[1])


def vin_keys(data: dict[str, Any]) -> list[tuple[str, int]]:
    """X-401 reports 'vin'; X-404 reports 'vin1' (and possibly more)."""
    keys = [(KEY_VIN, 1)] if KEY_VIN in data else []
    return keys + indexed_keys(data, KEY_VIN)


def parse_value(value: Any) -> tuple[float | None, str | None]:
    """Split a state value like '77.3', '77.3 F' or 'x.x' into (number, unit)."""
    if value is None:
        return None, None
    match = _NUMBER_RE.match(str(value))
    if not match:
        return None, None  # includes 'x.x' (sensor not readable / not configured)
    unit = match.group(2) or None
    return float(match.group(1)), unit


def to_float(value: Any) -> float | None:
    return parse_value(value)[0]


def is_configured(value: Any) -> bool:
    """Unconfigured/disconnected I/O is reported by the device as 'x.x'."""
    return value is not None and str(value).strip() not in ("", "x.x")
