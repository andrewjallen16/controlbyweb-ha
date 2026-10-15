"""Pure-logic tests (no Home Assistant instance needed)."""
from custom_components.controlbyweb.const import (
    MODELS,
    build_name_map,
    describe_state,
    guess_model,
    humanize_name,
    indexed_keys,
    is_configured,
    parse_value,
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
