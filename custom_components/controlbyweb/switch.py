"""Relays as switches, plus a pulse service with a custom duration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBWConfigEntry
from .const import (
    ATTR_DURATION,
    MAX_PULSE,
    MIN_PULSE,
    PREFIX_RELAY,
    RELAY_OFF,
    RELAY_ON,
    RELAY_PULSE,
    SERVICE_PULSE,
    indexed_keys,
    to_float,
)
from .entity import CBWEntity, async_setup_dynamic


def _build(entry: CBWConfigEntry, coordinator) -> list[CBWRelaySwitch]:
    return [
        CBWRelaySwitch(coordinator, key, n)
        for key, n in indexed_keys(coordinator.data, PREFIX_RELAY)
    ]


async def async_setup_entry(
    hass: HomeAssistant, entry: CBWConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_dynamic(entry, async_add_entities, _build)
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_PULSE,
        {
            vol.Required(ATTR_DURATION): vol.All(
                vol.Coerce(float), vol.Range(min=MIN_PULSE, max=MAX_PULSE)
            )
        },
        "async_pulse",
    )


class CBWRelaySwitch(CBWEntity, SwitchEntity):
    _attr_translation_key = "relay"

    def __init__(self, coordinator, key: str, number: int) -> None:
        super().__init__(coordinator, key, number)
        self._number = number

    @property
    def is_on(self) -> bool | None:
        value = to_float(self._raw)
        return None if value is None else value >= 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_send(**{self._key: RELAY_ON})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send(**{self._key: RELAY_OFF})

    async def async_pulse(self, duration: float) -> None:
        """Pulse for `duration` seconds. The device requires pulseTime to come
        before the relay command, and it applies to this one pulse only."""
        await self.coordinator.async_send(
            **{f"pulseTime{self._number}": duration, self._key: RELAY_PULSE}
        )
