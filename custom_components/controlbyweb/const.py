"""Constants for the ControlByWeb integration."""
from __future__ import annotations

import re
from typing import Any

from homeassistant.const import Platform

DOMAIN = "controlbyweb"

CONF_SSL = "ssl"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ONEWIRE_UNIT = "onewire_unit"
CONF_SHOW_UNITS = "show_units"
CONF_MODEL = "model"

DEFAULT_PORT = 80
DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 5  # seconds
MIN_SCAN_INTERVAL = 3  # devices report minRecRefresh = 3
UNIT_NONE = "none"

MODELS = [
    "X-400",
    "X-400C",
    "X-401",
    "X-404",
    "X-405",
    "X-406",
    "X-408",
    "X-410",
    "X-412",
    "X-417",
    "X-418",
    "X-420",
    "Other 400 series",
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


def _configured(data: dict[str, Any], prefix: str) -> list[str]:
    return [k for k, _ in indexed_keys(data, prefix) if is_configured(data[k])]


def guess_model(data: dict[str, Any]) -> str:
    """Best guess from the I/O the device reports (the user confirms it).

    state.json carries no model name, and modules can mirror remote I/O from other
    modules (P2P), so this is only a hint. An X-401 and an X-404 or X-400 that
    mirror 2 relays + 2 inputs look identical; that case defaults to X-401.
    """
    relays = len(indexed_keys(data, PREFIX_RELAY))
    inputs = len(indexed_keys(data, PREFIX_DIGITAL_INPUT))
    analog_in = len(_configured(data, PREFIX_ANALOG_INPUT))
    registers = len(_configured(data, PREFIX_REGISTER))
    one_wire = len(_configured(data, PREFIX_ONE_WIRE))

    if indexed_keys(data, PREFIX_DIGITAL_IO) or KEY_FREQUENCY_INPUT in data:
        return "X-420"
    if indexed_keys(data, PREFIX_ANALOG_OUTPUT):
        return "X-417"
    if analog_in:
        if relays:
            return "X-412"
        return "X-418" if analog_in > 4 else "X-420"
    if relays == 0 and inputs >= 8:
        return "X-408"
    if relays >= 4 and inputs >= 4:
        return "X-410"
    if relays == 2 and inputs == 2:
        return "X-401"
    if relays == 0 and inputs == 0 and one_wire:
        return "X-405"
    if relays == 0 and inputs == 0 and registers:
        return "X-404"
    return "Other 400 series"


def describe_state(data: dict[str, Any]) -> str:
    """Short human summary of the I/O found, e.g. '2 relays, 2 digital inputs'."""
    parts = []
    for label, plural, prefix in (
        ("relay", "relays", PREFIX_RELAY),
        ("digital input", "digital inputs", PREFIX_DIGITAL_INPUT),
        ("digital I/O", "digital I/O", PREFIX_DIGITAL_IO),
        ("analog input", "analog inputs", PREFIX_ANALOG_INPUT),
        ("analog output", "analog outputs", PREFIX_ANALOG_OUTPUT),
        ("1-Wire sensor", "1-Wire sensors", PREFIX_ONE_WIRE),
        ("register", "registers", PREFIX_REGISTER),
    ):
        n = len(_configured(data, prefix))
        if n:
            parts.append(f"{n} {label if n == 1 else plural}")
    return ", ".join(parts) or "no I/O assigned yet"
