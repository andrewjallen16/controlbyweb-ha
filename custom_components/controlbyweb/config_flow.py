"""Config flow: manual setup, DHCP discovery, reauth and options."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .api import CBWAuthError, CBWConnectionError, CBWError, create_client, detect_client
from .const import (
    CONF_MODEL,
    CONF_ONEWIRE_UNIT,
    CONF_SCAN_INTERVAL,
    CONF_SHOW_UNITS,
    CONF_SSL,
    CONF_USE_DEVICE_NAMES,
    CONF_VERIFY_SSL,
    CONF_WRITABLE_REGISTERS,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    KEY_SERIAL,
    MIN_SCAN_INTERVAL,
    MODELS,
    UNIT_NONE,
    describe_state,
    guess_model,
)
from .helpers import get_session

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


class CBWConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._state: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return CBWOptionsFlow()

    async def _async_connect(self, user_input: Mapping[str, Any]) -> str | None:
        """Try to connect. Returns an error key, or None (state kept for the next step)."""
        data = {**self._data, **user_input}
        try:
            client, state = await detect_client(get_session(self.hass, data), data)
        except CBWAuthError:
            return "invalid_auth"
        except CBWConnectionError:
            return "cannot_connect"
        except CBWError:
            return "unsupported_device"
        # 400 series report a serial number (their MAC); fall back to host:port
        uid = str(state.get(KEY_SERIAL) or f"{data[CONF_HOST]}:{data[CONF_PORT]}")
        await self.async_set_unique_id(uid)
        self._data = {**data, CONF_SHOW_UNITS: client.show_units}
        self._abort_if_unique_id_configured(updates=self._data)
        self._state = state
        return None

    # ------------------------------------------------------------------ manual
    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if (error := await self._async_connect(user_input)) is None:
                return await self.async_step_model()
            errors["base"] = error

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                vol.Optional(CONF_PASSWORD, default=""): PASSWORD_SELECTOR,
                vol.Required(CONF_SSL, default=False): bool,
                vol.Required(CONF_VERIFY_SSL, default=False): bool,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    # --------------------------------------------------------------- discovery
    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
        """A ControlByWeb MAC (00:0C:C8:...) appeared. If already set up, just follow
        its new IP address; otherwise offer to add it."""
        mac = format_mac(discovery_info.macaddress).upper()  # same form as serialNumber
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.ip})
        self._data = {CONF_HOST: discovery_info.ip, CONF_PORT: DEFAULT_PORT}
        self.context["title_placeholders"] = {"name": f"ControlByWeb {discovery_info.ip}"}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if (error := await self._async_connect(user_input)) is None:
                return await self.async_step_model()
            errors["base"] = error
        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                    vol.Optional(CONF_PASSWORD, default=""): PASSWORD_SELECTOR,
                }
            ),
            description_placeholders={"host": self._data[CONF_HOST]},
            errors=errors,
        )

    # ------------------------------------------------------------------- model
    async def async_step_model(self, user_input=None) -> ConfigFlowResult:
        """Confirm the model; it is shown on the device in Home Assistant."""
        if user_input is not None:
            model = user_input[CONF_MODEL]
            return self.async_create_entry(
                title=f"ControlByWeb {model} ({self._data[CONF_HOST]})",
                data={**self._data, CONF_MODEL: model},
            )
        return self.async_show_form(
            step_id="model",
            data_schema=vol.Schema(
                {vol.Required(CONF_MODEL, default=guess_model(self._state)): vol.In(MODELS)}
            ),
            description_placeholders={"summary": describe_state(self._state)},
        )

    # ------------------------------------------------------------------ reauth
    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            new_data = {**entry.data, **user_input}
            client = create_client(get_session(self.hass, new_data), new_data)
            try:
                await client.get_state()
            except CBWAuthError:
                errors["base"] = "invalid_auth"
            except CBWError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(entry, data=new_data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
                    ): str,
                    vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
                }
            ),
            errors=errors,
        )


class CBWOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        opts, data = self.config_entry.options, self.config_entry.data
        model = opts.get(CONF_MODEL) or data.get(CONF_MODEL) or MODELS[0]
        if model not in MODELS:
            model = MODELS[-1]
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODEL, default=model): vol.In(MODELS),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL, max=3600)),
                    vol.Required(
                        CONF_ONEWIRE_UNIT,
                        default=opts.get(CONF_ONEWIRE_UNIT, UNIT_NONE),
                    ): vol.In([UNIT_NONE, "\u00b0F", "\u00b0C"]),
                    vol.Required(
                        CONF_USE_DEVICE_NAMES,
                        default=opts.get(CONF_USE_DEVICE_NAMES, False),
                    ): bool,
                    vol.Required(
                        CONF_WRITABLE_REGISTERS,
                        default=opts.get(CONF_WRITABLE_REGISTERS, False),
                    ): bool,
                }
            ),
        )
