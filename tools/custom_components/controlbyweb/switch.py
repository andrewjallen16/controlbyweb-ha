"""Relays as switches."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBWConfigEntry
from .const import PREFIX_RELAY, RELAY_OFF, RELAY_ON, indexed_keys, to_float
from .entity import CBWEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: CBWConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        CBWRelaySwitch(coordinator, key, f"Relay {n}")
        for key, n in indexed_keys(coordinator.data, PREFIX_RELAY)
    )


class CBWRelaySwitch(CBWEntity, SwitchEntity):
    @property
    def is_on(self) -> bool | None:
        value = to_float(self._raw)
        return None if value is None else value >= 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_send(**{self._key: RELAY_ON})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send(**{self._key: RELAY_OFF})
