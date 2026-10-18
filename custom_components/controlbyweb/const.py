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
CONF_FREQUENCY_UNIT = "frequency_unit"
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
SERVICE_START_TIMER = "start_timer"
MAX_TIMER = 16_777_215  # timers are 24-bit, 1 second resolution (400 series manual)
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
PREFIX_TIMER = "timer"  # name unconfirmed: the manuals list timers but not their state.json tag
KEY_FREQUENCY_INPUT = "frequencyInput"  # X-420 dedicated input; real units report "frequencyInput1"
KEY_VIN = "vin"  # some units report "vin", others "vin1"
KEY_SERIAL = "serialNumber"

# Keys that are device info rather than I/O (excluded when matching custom names)
NON_IO_KEYS = frozenset(
    {
        "lat", "long", "utcTime", "timezoneOffset", KEY_SERIAL,
        "minRecRefresh", "deviceUptime", "downloadSettings",
    }
)

_HANDLED_KEYS = (
    PREFIX_RELAY, PREFIX_DIGITAL_INPUT, PREFIX_DIGITAL_IO, PREFIX_ONE_WIRE, PREFIX_ANALOG_INPUT,
    PREFIX_ANALOG_OUTPUT, PREFIX_REGISTER, PREFIX_ON_TIME, PREFIX_TOTAL_ON_TIME, PREFIX_COUNT,
    PREFIX_FREQUENCY, PREFIX_TIMER, KEY_FREQUENCY_INPUT, KEY_VIN,
)

_MODEL_RE = re.compile(r"^\s*(X-\d{3}[A-Z]?)", re.IGNORECASE)
_UPTIME_RE = re.compile(r"^\s*(?:(\d+)\s*d(?:ays?)?\s+)?(\d+):(\d{2}):(\d{2})\s*$", re.IGNORECASE)

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
_NUMBER_RE = re.compile(r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*?)\s*$")
_NAME_SPLIT_RE = re.compile(
    r"(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Za-z])|(?<=[A-Z])(?=[A-Z][a-z])"
)

# Units as printed by the device -> Home Assistant units (matched case-insensitively)
_UNIT_ALIASES = {
    "f": "\u00b0F", "c": "\u00b0C", "%rh": "%",
    "mph": "mph", "km/h": "km/h", "kph": "km/h", "kmh": "km/h", "m/s": "m/s", "mps": "m/s",
    "kn": "kn", "kt": "kn", "kts": "kn", "knot": "kn", "knots": "kn",
    "v": "V", "mv": "mV", "a": "A", "ma": "mA", "w": "W", "kw": "kW", "va": "VA", "var": "var",
    "hz": "Hz", "kwh": "kWh", "wh": "Wh", "deg": "\u00b0", "degrees": "\u00b0", "\u00b0": "\u00b0",
}
# Normalised unit -> Home Assistant device class value (used for registers / analog inputs,
# e.g. the readings of a Modbus power meter behind an X-404)
UNIT_DEVICE_CLASS = {
    "V": "voltage", "mV": "voltage",
    "A": "current", "mA": "current",
    "W": "power", "kW": "power",
    "VA": "apparent_power", "var": "reactive_power",
    "Hz": "frequency",
    "kWh": "energy", "Wh": "energy",
    "\u00b0C": "temperature", "\u00b0F": "temperature",
}
SPEED_UNITS = frozenset({"mph", "km/h", "m/s", "kn"})
FREQUENCY_UNIT_CHOICES = [UNIT_NONE, "Hz", "mph", "km/h", "m/s", "knots"]


def normalize_unit(raw: str | None) -> str | None:
    """'F' -> degrees F, 'Knots' -> 'kn'; unknown units are passed through unchanged."""
    if not raw:
        return None
    raw = raw.strip()
    return _UNIT_ALIASES.get(raw.lower(), raw)


def indexed_keys(data: dict[str, Any], prefix: str) -> list[tuple[str, int]]:
    """Return [(key, number)] for keys like '<prefix><N>' sorted by N."""
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    found = []
    for key in data:
        if match := pattern.match(key):
            found.append((key, int(match.group(1))))
    return sorted(found, key=lambda item: item[1])


def unhandled_keys(data: dict[str, Any]) -> list[str]:
    """Keys in state.json this integration doesn't use (for logs and diagnostics)."""
    return sorted(
        key
        for key in data
        if key not in NON_IO_KEYS
        and not any(re.fullmatch(rf"{re.escape(p)}\d*", key) for p in _HANDLED_KEYS)
    )


def vin_keys(data: dict[str, Any]) -> list[tuple[str, int]]:
    """X-401 reports 'vin'; X-404 reports 'vin1' (and possibly more)."""
    keys = [(KEY_VIN, 1)] if KEY_VIN in data else []
    return keys + indexed_keys(data, KEY_VIN)


def frequency_input_keys(data: dict[str, Any]) -> list[tuple[str, int]]:
    """X-420 units report 'frequencyInput1'; accept plain 'frequencyInput' too."""
    keys = [(KEY_FREQUENCY_INPUT, 1)] if KEY_FREQUENCY_INPUT in data else []
    return keys + indexed_keys(data, KEY_FREQUENCY_INPUT)


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


_UNREADABLE_RE = re.compile(r"^x\.x(\s|$)", re.IGNORECASE)


def is_configured(value: Any) -> bool:
    """Unconfigured/disconnected I/O is reported as 'x.x' (possibly followed by a
    unit when showUnits is on, e.g. 'x.x F')."""
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and not _UNREADABLE_RE.match(text)


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

    if indexed_keys(data, PREFIX_DIGITAL_IO) or frequency_input_keys(data):
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
        ("timer", "timers", PREFIX_TIMER),
    ):
        n = len(_configured(data, prefix))
        if n:
            parts.append(f"{n} {label if n == 1 else plural}")
    return ", ".join(parts) or "no I/O assigned yet"


def model_from_number(model_number: str | None) -> str | None:
    """'X-404-I' (as reported by diagnostics.xml) -> 'X-404', matched against MODELS."""
    if not model_number or not (match := _MODEL_RE.match(str(model_number))):
        return None
    model = match.group(1).upper()
    return model if model in MODELS else "Other 400 series"


def parse_uptime(value: Any) -> int | None:
    """'1 days 22:12:23' -> seconds (166343). Returns None for anything else."""
    if value is None or not (match := _UPTIME_RE.match(str(value))):
        return None
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


# ---- power source (PoE vs DC). From the 400 series manual: "-E" models are Power Over Ethernet
# and/or 9-28 VDC, "-I" models are DC only. A PoE-powered module reads 0 V on Vin; an -E module
# draws from PoE while Vin is below 12 V and from the DC input above 12 V.
POE_VIN_THRESHOLD = 1.0  # below this the Vin terminals are not supplying power
POE_PRIORITY_VOLTAGE = 12.0
POWER_SOURCES = ["poe", "dc_input"]


def is_poe_model(model_number: str | None) -> bool:
    """'X-420-E' -> True (PoE capable); 'X-404-I' -> False (DC only)."""
    return bool(model_number) and re.search(r"-E$", str(model_number).strip(), re.IGNORECASE) is not None


def power_source(vin: float | None, poe_model: bool) -> str | None:
    """'poe' or 'dc_input' from the Vin reading. A module we can talk to that reads ~0 V on
    Vin must be powered over Ethernet, whatever its model."""
    if vin is None:
        return None
    if vin < POE_VIN_THRESHOLD:
        return "poe"
    if poe_model and vin <= POE_PRIORITY_VOLTAGE:
        return "poe"
    return "dc_input"
