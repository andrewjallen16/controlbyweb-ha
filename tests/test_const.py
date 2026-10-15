"""Pure-logic tests (no Home Assistant instance needed)."""
from custom_components.controlbyweb.const import (
    MODELS,
    build_name_map,
    describe_state,
    frequency_input_keys,
    guess_model,
    humanize_name,
    indexed_keys,
    is_configured,
    normalize_unit,
    parse_value,
    UNIT_DEVICE_CLASS,
    unhandled_keys,
    vin_keys,
)


def test_parse_value():
    assert parse_value("77.3 F") == (77.3, "F")
    assert parse_value("91.29") == (91.29, None)
    assert parse_value("0") == (0.0, None)
    assert parse_value("-4.5 C") == (-4.5, "C")
    assert parse_value("x.x") == (None, None)
    assert parse_value("") == (None, None)
    assert parse_value(None) == (None, None)


def test_is_configured():
    assert is_configured("0") and is_configured("12.5 F")
    assert not is_configured("x.x") and not is_configured("") and not is_configured(None)


def test_indexed_keys_do_not_collide():
    data = {"onTime1": "0", "totalOnTime1": "0", "frequency1": "0", "frequencyInput": "1",
            "digitalInput1": "0", "digitalIO1": "0", "count1": "0"}
    assert [k for k, _ in indexed_keys(data, "onTime")] == ["onTime1"]
    assert [k for k, _ in indexed_keys(data, "frequency")] == ["frequency1"]
    assert [k for k, _ in indexed_keys(data, "digitalInput")] == ["digitalInput1"]


def test_vin_both_spellings():
    assert vin_keys({"vin": "12"}) == [("vin", 1)]
    assert vin_keys({"vin1": "12"}) == [("vin1", 1)]


def test_guess_model():
    ten = {f"relay{i}": "0" for i in range(1, 5)} | {f"digitalInput{i}": "0" for i in range(1, 5)}
    assert guess_model(ten) == "X-410"
    assert guess_model({f"digitalInput{i}": "0" for i in range(1, 9)}) == "X-408"
    assert guess_model({"relay1": "0", "relay2": "0", "digitalInput1": "0", "digitalInput2": "0"}) == "X-401"
    assert guess_model({"analogInput1": "1", "digitalIO1": "0"}) == "X-420"
    assert guess_model({"relay1": "0", "analogInput1": "1"}) == "X-412"
    assert guess_model({"analogOutput1": "0"}) == "X-417"
    assert guess_model({f"analogInput{i}": "1" for i in range(1, 9)}) == "X-418"
    assert guess_model({"register1": "1.5"}) == "X-404"
    assert guess_model({"oneWireSensor1": "70 F"}) == "X-405"
    assert guess_model({"relay1": "0"}) == "Other 400 series"
    assert guess_model({"relay1": "0"}) in MODELS


def test_describe_state():
    assert describe_state({"relay1": "0", "relay2": "0", "digitalInput1": "0"}) == "2 relays, 1 digital input"
    assert describe_state({}) == "no I/O assigned yet"


def test_humanize_name():
    assert humanize_name("gasTank") == "Gas Tank"
    assert humanize_name("myRegister1") == "My Register 1"
    assert humanize_name("hVACFan") == "HVAC Fan"
    assert humanize_name("zone2Pump") == "Zone 2 Pump"


def test_build_name_map_matches_by_position():
    state = {"relay1": "0", "relay2": "1", "digitalInput1": "0", "vin": "12.2", "utcTime": "1"}
    custom = {"garageDoor": "0", "relay2": "1", "frontGate": "0", "vin": "12.2", "utcTime": "1"}
    assert build_name_map(state, custom) == {"relay1": "Garage Door", "digitalInput1": "Front Gate"}


def test_build_name_map_refuses_when_unsure():
    state = {"relay1": "0", "relay2": "1", "digitalInput1": "0", "vin": "12.2"}
    assert build_name_map(state, {"a": "0"}) == {}  # different number of entries
    disagree = {"garageDoor": "9", "relay2": "0", "frontGate": "7", "vin": "55"}
    assert build_name_map(state, disagree) == {}  # values disagree


REAL_X420 = {
    "digitalIO1": "0", "digitalIO2": "0", "analogInput1": "-0", "analogInput2": "-24.18",
    "analogInput3": "-0.01", "analogInput4": "5", "frequencyInput1": "0.0", "vin": "22.3",
    "register1": "0", "lat": "41.6796", "long": "-111.8737", "utcTime": "1791710310",
    "timezoneOffset": "-18000", "serialNumber": "00:0C:C8:06:E9:9A", "minRecRefresh": "3",
    "downloadSettings": "1",
}


def test_frequency_input_numbered_and_plain():
    assert frequency_input_keys({"frequencyInput1": "0.0"}) == [("frequencyInput1", 1)]
    assert frequency_input_keys({"frequencyInput": "0.0"}) == [("frequencyInput", 1)]
    assert frequency_input_keys({"frequency1": "0"}) == []  # input function, not the X-420 input


def test_real_x420_is_recognised():
    assert guess_model(REAL_X420) == "X-420"
    assert describe_state(REAL_X420) == "2 digital I/O, 4 analog inputs, 1 register"


def test_unreadable_values_include_unit_suffix():
    for value in ("x.x", "X.X", " x.x ", "x.x F", "", None):
        assert not is_configured(value), value
    for value in ("0", "-0", "91.29 F", "x.xy"):
        assert is_configured(value), value


def test_normalize_unit():
    assert normalize_unit("F") == "\u00b0F"
    assert normalize_unit("c") == "\u00b0C"
    assert normalize_unit("Knots") == "kn"
    assert normalize_unit("MPH") == "mph"
    assert normalize_unit("kph") == "km/h"
    assert normalize_unit("psi") == "psi"  # unknown units pass through
    assert normalize_unit(None) is None


def test_unhandled_keys():
    assert unhandled_keys(REAL_X420) == []  # everything the real X-420 reports is understood or device info
    assert unhandled_keys({**REAL_X420, "timer1": "0"}) == []  # timers are handled
    assert unhandled_keys({"relay1": "0", "mysteryTag": "1", "counter7": "2"}) == ["counter7", "mysteryTag"]


def test_power_meter_units():
    # readings of a Modbus power meter behind an X-404 (as seen in Home Assistant)
    assert normalize_unit("A") == "A" and UNIT_DEVICE_CLASS["A"] == "current"
    assert normalize_unit("V") == "V" and UNIT_DEVICE_CLASS["V"] == "voltage"
    assert normalize_unit("W") == "W" and UNIT_DEVICE_CLASS["W"] == "power"
    assert normalize_unit("VA") == "VA" and UNIT_DEVICE_CLASS["VA"] == "apparent_power"
    assert normalize_unit("Deg") == "\u00b0" and "\u00b0" not in UNIT_DEVICE_CLASS  # no HA class for angles
    assert normalize_unit("kwh") == "kWh" and UNIT_DEVICE_CLASS["kWh"] == "energy"
    assert normalize_unit("hz") == "Hz" and normalize_unit("Hz") == "Hz"
    assert normalize_unit("psi") == "psi" and "psi" not in UNIT_DEVICE_CLASS  # unknown units pass through
    assert parse_value("-91.3 Deg") == (-91.3, "Deg")
