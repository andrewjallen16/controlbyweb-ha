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


@pytest.fixture
def device(aioclient_mock):
    """A fake 400 series module answering state.json."""
    aioclient_mock.get(STATE_URL, json=dict(STATE))
    return aioclient_mock


@pytest.fixture
def entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, unique_id=UID, data=dict(ENTRY_DATA), title="test")
