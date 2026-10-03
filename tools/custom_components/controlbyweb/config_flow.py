"""Config flow."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CBWAuthError, CBWError, CBWJsonClient, create_client, detect_client
from .const import (
    CONF_MODEL,
    CONF_ONEWIRE_UNIT,
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_SHOW_UNITS,
    CONF_SSL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    KEY_SERIAL,
    MIN_SCAN_INTERVAL,
    MODEL_UNSPECIFIED,
    MODELS,
    UNIT_NONE,
)


async def _detect(hass: HomeAssistant, data: Mapping[str, Any]):
    ssl = data.get(CONF_SSL, False)
    session = async_get_clientsession(hass, verify_ssl=not ssl)
    client, state = await detect_client(session, data)
    detected = {CONF_PROTOCOL: client.protocol}
    if isinstance(client, CBWJsonClient):
        detected[CONF_SHOW_UNITS] = client.show_units
    return detected, state


class CBWConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return CBWOptionsFlow()

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                detected, state = await _detect(self.hass, user_input)
            except CBWAuthError:
                errors["base"] = "invalid_auth"
            except CBWError:
                errors["base"] = "cannot_connect"
            else:
                # 400 series report a serial/MAC; older WebRelays do not.
                uid = str(
                    state.get(KEY_SERIAL)
                    or f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                )
                await self.async_set_unique_id(uid)
                data = {**user_input, **detected}
                self._abort_if_unique_id_configured(updates=data)
                return self.async_create_entry(
                    title=f"ControlByWeb {user_input[CONF_HOST]}", data=data
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                vol.Optional(CONF_PASSWORD, default=""): str,
                vol.Required(CONF_SSL, default=False): bool,
                vol.Required(CONF_MODEL, default=MODEL_UNSPECIFIED): vol.In(MODELS),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            new_data = {**entry.data, **user_input}
            ssl = new_data.get(CONF_SSL, False)
            client = create_client(async_get_clientsession(self.hass, verify_ssl=not ssl), new_data)
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
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )


class CBWOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        opts = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL, max=3600)),
                    vol.Required(
                        CONF_ONEWIRE_UNIT,
                        default=opts.get(CONF_ONEWIRE_UNIT, UNIT_NONE),
                    ): vol.In([UNIT_NONE, "\u00b0F", "\u00b0C"]),
                }
            ),
        )
