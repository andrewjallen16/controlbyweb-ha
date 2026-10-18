"""Setup, entities, services and diagnostics (need pytest-homeassistant-custom-component)."""
from datetime import timedelta

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.controlbyweb.const import DOMAIN
from custom_components.controlbyweb.diagnostics import async_get_config_entry_diagnostics

from .conftest import CUSTOM_URL, DIAG_URL, HOST, STATE, STATE_URL, UID, mock_diagnostics


def _eid(hass, domain, key):
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{UID}_{key}")


def _device(hass, entry):
    """The module's device. (device_registry.async_get_device is deprecated: identifiers are no
    longer unique across config entries, so look the device up through its config entry.)"""
    return dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]


def _registered(hass):
    """Everything this integration registered, as 'domain:key' (for failure messages)."""
    registry = er.async_get(hass)
    return sorted(
        f"{ent.domain}:{(ent.unique_id or '').removeprefix(UID + '_')}"
        for ent in registry.entities.values()
        if ent.platform == DOMAIN
    )


async def _setup(hass, entry):
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_entities_created(hass, device, entry):
    await _setup(hass, entry)
    for domain, key in (
        ("switch", "relay1"), ("switch", "relay2"), ("button", "relay1"),
        ("binary_sensor", "digitalInput1"), ("sensor", "oneWireSensor1"),
        ("sensor", "vin1"), ("sensor", "register1"),
    ):
        assert _eid(hass, domain, key), (domain, key, "registered:", _registered(hass))
    # unused slots ("x.x") are skipped, and registers are read-only sensors by default
    assert not _eid(hass, "sensor", "oneWireSensor2")
    assert not _eid(hass, "sensor", "register2")
    assert not _eid(hass, "number", "register1")


async def test_switch_turn_on_sends_command(hass, device, entry):
    await _setup(hass, entry)
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": _eid(hass, "switch", "relay1")}, blocking=True
    )
    assert any("relay1=1" in str(call[1]) for call in device.mock_calls)


async def test_pulse_service_puts_pulse_time_before_relay(hass, device, entry):
    await _setup(hass, entry)
    await hass.services.async_call(
        DOMAIN, "pulse",
        {"entity_id": _eid(hass, "switch", "relay1"), "duration": 5},
        blocking=True,
    )
    urls = [str(call[1]) for call in device.mock_calls if "relay1=2" in str(call[1])]
    assert urls and urls[0].index("pulseTime1") < urls[0].index("relay1=2")


async def test_new_sensor_appears_without_reload(hass, aioclient_mock, entry):
    aioclient_mock.get(STATE_URL, json=dict(STATE))
    mock_diagnostics(aioclient_mock)
    await _setup(hass, entry)
    assert not _eid(hass, "sensor", "oneWireSensor2")

    aioclient_mock.clear_requests()
    aioclient_mock.get(STATE_URL, json={**STATE, "oneWireSensor2": "70.5 F"})
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=30))
    await hass.async_block_till_done()
    assert _eid(hass, "sensor", "oneWireSensor2")


async def test_device_names_are_opt_in(hass, aioclient_mock, entry):
    # Same I/O in the same order as STATE (names are matched by position):
    # vin1, register1, register2, relay1, relay2, digitalInput1, digitalInput2, oneWire1, oneWire2
    custom = {"vin1": "25.0", "register1": "0", "register2": "x.x",
              "garageDoor": "0", "relay2": "0", "frontGate": "1", "digitalInput2": "0",
              "oneWireSensor1": "91.29 F", "oneWireSensor2": "x.x"}
    aioclient_mock.get(CUSTOM_URL, json=custom)
    aioclient_mock.get(STATE_URL, json=dict(STATE))
    mock_diagnostics(aioclient_mock)
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"use_device_names": True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get(_eid(hass, "switch", "relay1"))
    assert state.attributes["friendly_name"].endswith("Garage Door")


async def test_diagnostics_redacts_secrets(hass, device, entry):
    await _setup(hass, entry)
    device.get(CUSTOM_URL, json={})
    diag = await async_get_config_entry_diagnostics(hass, entry)
    blob = str(diag)
    for secret in ("secret", HOST, UID, "41.6796", "-111.8737"):
        assert secret not in blob


async def test_timer_start_service_and_cancel_button(hass, aioclient_mock, entry):
    aioclient_mock.get(STATE_URL, json={**STATE, "timer1": "0"})
    mock_diagnostics(aioclient_mock)
    await _setup(hass, entry)
    timer, cancel = _eid(hass, "sensor", "timer1"), _eid(hass, "button", "timer1")
    assert timer and cancel

    await hass.services.async_call(
        DOMAIN, "start_timer", {"entity_id": timer, "duration": 30}, blocking=True
    )
    assert any("timer1=30" in str(call[1]) for call in aioclient_mock.mock_calls)

    await hass.services.async_call("button", "press", {"entity_id": cancel}, blocking=True)
    assert any("timer1=0" in str(call[1]) for call in aioclient_mock.mock_calls)


async def test_start_timer_on_a_non_timer_sensor_is_refused(hass, device, entry):
    await _setup(hass, entry)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "start_timer",
            {"entity_id": _eid(hass, "sensor", "vin1"), "duration": 30},
            blocking=True,
        )


async def test_device_card_shows_model_and_firmware(hass, device, entry):
    await _setup(hass, entry)
    dev = _device(hass, entry)
    assert dev.model == "X-404-I"
    assert dev.sw_version == "3.13.8.0"


async def test_setup_works_without_diagnostics_xml(hass, aioclient_mock, entry):
    aioclient_mock.get(STATE_URL, json=dict(STATE))
    aioclient_mock.get(DIAG_URL, status=404)  # older firmware
    await _setup(hass, entry)
    dev = _device(hass, entry)
    assert dev.sw_version is None
    assert dev.model == "X-404"  # falls back to the model chosen at setup


async def test_uptime_sensor(hass, device, entry):
    await _setup(hass, entry)
    entity_id = _eid(hass, "sensor", "deviceUptime")
    assert entity_id
    state = hass.states.get(entity_id)
    unit = state.attributes["unit_of_measurement"]  # seconds, or hours via the suggested unit
    seconds = float(state.state) * {"s": 1, "min": 60, "h": 3600, "d": 86400}[unit]
    assert abs(seconds - 166320) < 400  # 1 d 22:12:23, rounded down to the minute
    assert state.attributes["device_class"] == "duration"


async def test_poe_powered_module_has_no_zero_volt_supply_sensor(hass, aioclient_mock, entry):
    aioclient_mock.get(STATE_URL, json={**STATE, "vin1": "0"})  # PoE: Vin terminals read 0 V
    mock_diagnostics(aioclient_mock, model="X-404-E")
    await _setup(hass, entry)
    assert not _eid(hass, "sensor", "vin1")
    source = _eid(hass, "sensor", "powerSource")
    assert source
    assert hass.states.get(source).state == "poe"


async def test_dc_powered_poe_capable_module(hass, aioclient_mock, entry):
    aioclient_mock.get(STATE_URL, json=dict(STATE))  # vin1 = 25.0 V
    mock_diagnostics(aioclient_mock, model="X-404-E")
    await _setup(hass, entry)
    assert _eid(hass, "sensor", "vin1")
    assert hass.states.get(_eid(hass, "sensor", "powerSource")).state == "dc_input"


async def test_dc_only_module_has_supply_voltage_but_no_power_source(hass, device, entry):
    await _setup(hass, entry)  # X-404-I on 25 V
    assert _eid(hass, "sensor", "vin1")
    assert not _eid(hass, "sensor", "powerSource")


async def test_existing_zero_volt_supply_entity_is_removed_once(hass, aioclient_mock, entry):
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create("sensor", DOMAIN, f"{UID}_vin1", config_entry=entry)
    aioclient_mock.get(STATE_URL, json={**STATE, "vin1": "0"})
    mock_diagnostics(aioclient_mock, model="X-404-E")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert not _eid(hass, "sensor", "vin1")


async def test_poe_module_without_vin_in_state_uses_diagnostics_xml(hass, aioclient_mock, entry):
    # older firmware: no Vin in state.json, but diagnostics.xml says <vin>POE</vin>
    state = {k: v for k, v in STATE.items() if k != "vin1"}
    aioclient_mock.get(STATE_URL, json=state)
    mock_diagnostics(aioclient_mock, model="X-401-E", vin="POE")
    await _setup(hass, entry)
    assert not _eid(hass, "sensor", "vin1")
    assert hass.states.get(_eid(hass, "sensor", "powerSource")).state == "poe"
