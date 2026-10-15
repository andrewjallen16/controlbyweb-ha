"""Setup, entities, services and diagnostics (need pytest-homeassistant-custom-component)."""
from datetime import timedelta

from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.controlbyweb.const import DOMAIN
from custom_components.controlbyweb.diagnostics import async_get_config_entry_diagnostics

from .conftest import CUSTOM_URL, HOST, STATE, STATE_URL, UID


def _eid(hass, domain, key):
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{UID}_{key}")


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
