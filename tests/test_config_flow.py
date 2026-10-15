"""Config flow tests (need pytest-homeassistant-custom-component)."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from custom_components.controlbyweb.const import DOMAIN

from .conftest import ENTRY_DATA, HOST, STATE_URL, UID

USER_INPUT = {
    "host": HOST,
    "port": 80,
    "username": "admin",
    "password": "secret",
    "ssl": False,
    "verify_ssl": False,
}


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow_creates_entry(hass, device):
    with patch("custom_components.controlbyweb.async_setup_entry", return_value=True):
        result = await _start(hass)
        assert result["step_id"] == "user"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
        assert result["step_id"] == "model"
        assert result["description_placeholders"]["summary"].startswith("2 relays")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"model": "X-404"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"ControlByWeb X-404 ({HOST})"
    assert result["data"]["model"] == "X-404"
    assert result["result"].unique_id == UID


async def test_invalid_auth(hass, aioclient_mock):
    aioclient_mock.get(STATE_URL, status=401)
    result = await hass.config_entries.flow.async_configure(
        (await _start(hass))["flow_id"], USER_INPUT
    )
    assert result["errors"] == {"base": "invalid_auth"}


async def test_cannot_connect(hass, aioclient_mock):
    aioclient_mock.get(STATE_URL, exc=TimeoutError)
    result = await hass.config_entries.flow.async_configure(
        (await _start(hass))["flow_id"], USER_INPUT
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_unsupported_device(hass, aioclient_mock):
    aioclient_mock.get(STATE_URL, status=404)
    result = await hass.config_entries.flow.async_configure(
        (await _start(hass))["flow_id"], USER_INPUT
    )
    assert result["errors"] == {"base": "unsupported_device"}


async def test_dhcp_updates_host_of_known_device(hass, device, entry):
    entry.add_to_hass(hass)
    with patch("custom_components.controlbyweb.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(ip="192.168.1.77", hostname="cbw", macaddress="000cc807ecac"),
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data["host"] == "192.168.1.77"


async def test_dhcp_new_device_asks_for_login(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data=DhcpServiceInfo(ip="192.168.1.80", hostname="cbw", macaddress="000cc8064a06"),
    )
    assert result["step_id"] == "discovery_confirm"
