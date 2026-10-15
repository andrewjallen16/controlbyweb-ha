"""Constants and pure helpers for the ControlByWeb integration."""
from __future__ import annotations

import re
from typing import Any

from homeassistant.const import Platform

DOMAIN = "controlbyweb"

CONF_SSL = "ssl"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ONEWIRE_UNIT = "onewire_unit"
CONF_SHOW_UNITS = "show_units"
CONF_MODEL = "model"
CONF_USE_DEVICE_NAMES = "use_device_names"
CONF_WRITABLE_REGISTERS = "writable_registers"

DEFAULT_PORT = 80
DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 5  # seconds
MIN_SCAN_INTERVAL = 3  # devices report minRecRefresh = 3
UNIT_NONE = "none"

SERVICE_PULSE = "pulse"
ATTR_DURATION = "duration"
MIN_PULSE = 0.1  # seconds, per the manual
MAX_PULSE = 86400

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

# Key names as used in state.json
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

# Keys that are device info rather than I/O (excluded when matching custom names)
NON_IO_KEYS = frozenset(
    {"lat", "long", "utcTime", "timezoneOffset", KEY_SERIAL, "minRecRefresh", "deviceUptime"}
)

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
_NUMBER_RE = re.compile(r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*?)\s*$")
_NAME_SPLIT_RE = re.compile(
    r"(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Za-z])|(?<=[A-Z])(?=[A-Z][a-z])"
)

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
    return float(match.group(1)), (match.group(2) or None)


def to_float(value: Any) -> float | None:
    return parse_value(value)[0]


def is_configured(value: Any) -> bool:
    """Unconfigured/disconnected I/O is reported by the device as 'x.x'."""
    return value is not None and str(value).strip() not in ("", "x.x")


# ---------------------------------------------------------------- device names
def humanize_name(key: str) -> str:
    """'gasTank' -> 'Gas Tank', 'myRegister1' -> 'My Register 1'.

    customState.json only provides camelCase names, so spacing and capitalisation
    are reconstructed and may not match what you typed on the device exactly.
    """
    if not key:
        return key
    return _NAME_SPLIT_RE.sub(" ", key[0].upper() + key[1:])


def _values_match(a: Any, b: Any) -> bool:
    if str(a) == str(b):
        return True
    na, nb = to_float(a), to_float(b)
    if na is None or nb is None:
        return False
    return abs(na - nb) <= max(1.0, 0.05 * max(abs(na), abs(nb)))


def build_name_map(state: dict[str, Any], custom: dict[str, Any]) -> dict[str, str]:
    """Map state.json keys to the device's custom names, or {} if unsure.

    The manual says customState.json holds the same I/O keyed by camelCase custom
    names, but not how entries line up, so they are matched by position and the
    result is only trusted if both files have the same number of I/O entries and
    their values agree. Wrong labels on a relay are worse than generic ones.
    """
    state_keys = [k for k in state if k not in NON_IO_KEYS]
    custom_keys = [k for k in custom if k not in NON_IO_KEYS]
    if not state_keys or len(state_keys) != len(custom_keys):
        return {}
    pairs = list(zip(state_keys, custom_keys))
    mismatches = sum(1 for sk, ck in pairs if not _values_match(state[sk], custom[ck]))
    if mismatches > max(1, len(pairs) // 5):
        return {}
    return {sk: humanize_name(ck) for sk, ck in pairs if ck != sk}


# -------------------------------------------------------- model guess / summary
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
