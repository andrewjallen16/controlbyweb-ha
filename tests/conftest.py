"""Shared fixtures (needs pytest-homeassistant-custom-component)."""
from __future__ import annotations

import re

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.controlbyweb.const import DOMAIN

pytest_plugins = ["pytest_homeassistant_custom_component"]

HOST = "192.168.1.50"
UID = "00:0C:C8:07:EC:AC"
# yarl drops the default port, so the real request URL is http://HOST/state.json?... (no ":80")
STATE_URL = re.compile(rf"http://{re.escape(HOST)}(:80)?/state\.json.*")
CUSTOM_URL = re.compile(rf"http://{re.escape(HOST)}(:80)?/customState\.json.*")
DIAG_URL = re.compile(rf"http://{re.escape(HOST)}(:80)?/diagnostics\.xml.*")
DIAG_XML = (
    "<datavalues><modelNumber>X-404-I</modelNumber><firmwareRevision>3.13.8.0</firmwareRevision>"
    f"<serialNumber>{UID}</serialNumber><vin>25.1 V</vin><utcTime>1792289373</utcTime>"
    "<timezoneOffset>-25200</timezoneOffset><deviceUptime>1 days 22:12:23</deviceUptime></datavalues>"
)

STATE = {
    "vin1": "25.0",
    "register1": "0",
    "register2": "x.x",
    "relay1": "0",
    "relay2": "0",
    "digitalInput1": "1",
    "digitalInput2": "0",
    "oneWireSensor1": "91.29 F",
    "oneWireSensor2": "x.x",
    "lat": "41.6796",
    "long": "-111.8737",
    "serialNumber": UID,
    "deviceUptime": "1 days 22:12:23",
}

ENTRY_DATA = {
    "host": HOST,
    "port": 80,
    "username": "admin",
    "password": "secret",
    "ssl": False,
    "verify_ssl": False,
    "show_units": True,
    "model": "X-404",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading custom_components in every test."""
    yield


def mock_diagnostics(mocker) -> None:
    """The module also answers diagnostics.xml (model number, firmware)."""
    mocker.get(DIAG_URL, text=DIAG_XML)


@pytest.fixture
def device(aioclient_mock):
    """A fake 400 series module answering state.json and diagnostics.xml."""
    aioclient_mock.get(STATE_URL, json=dict(STATE))
    mock_diagnostics(aioclient_mock)
    return aioclient_mock


@pytest.fixture
def entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, unique_id=UID, data=dict(ENTRY_DATA), title="test")
