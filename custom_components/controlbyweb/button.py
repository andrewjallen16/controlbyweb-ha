"""Relay pulse buttons and counter/timer reset buttons."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBWConfigEntry
from .const import (
    PREFIX_COUNT,
    PREFIX_ON_TIME,
    PREFIX_RELAY,
    PREFIX_TIMER,
    PREFIX_TOTAL_ON_TIME,
    RELAY_PULSE,
    indexed_keys,
)
from .entity import CBWEntity, async_setup_dynamic


def _build(entry: CBWConfigEntry, coordinator) -> list[ButtonEntity]:
    data = coordinator.data
    entities: list[ButtonEntity] = [
        CBWPulseButton(coordinator, key, n) for key, n in indexed_keys(data, PREFIX_RELAY)
    ]
    for prefix, translation_key in (
        (PREFIX_COUNT, "reset_count"),
        (PREFIX_ON_TIME, "reset_on_time"),
        (PREFIX_TOTAL_ON_TIME, "reset_total_on_time"),
    ):
        entities += [
            CBWResetButton(coordinator, key, n, translation_key)
            for key, n in indexed_keys(data, prefix)
        ]
    entities += [
        CBWTimerCancelButton(coordinator, key, n) for key, n in indexed_keys(data, PREFIX_TIMER)
    ]
    return entities


async def async_setup_entry(
    hass: HomeAssistant, entry: CBWConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_dynamic(entry, async_add_entities, _build)


class CBWPulseButton(CBWEntity, ButtonEntity):
    """Pulses the relay for the Pulse Time set in the device's I/O setup."""

    _attr_translation_key = "relay_pulse"

    def __init__(self, coordinator, key: str, number: int) -> None:
        super().__init__(coordinator, key, number, name_suffix="pulse")

    async def async_press(self) -> None:
        await self.coordinator.async_send(**{self._key: RELAY_PULSE})


class CBWResetButton(CBWEntity, ButtonEntity):
    """Sets a counter / on-time / total-on-time back to 0 (documented device command)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, key: str, number: int, translation_key: str) -> None:
        super().__init__(coordinator, key, number, name_suffix="reset")
        self._attr_translation_key = translation_key

    async def async_press(self) -> None:
        await self.coordinator.async_send(**{self._key: 0})


class CBWTimerCancelButton(CBWEntity, ButtonEntity):
    """Stops a running timer (sets it to 0). Starting one is the start_timer service,
    because it needs a duration."""

    _attr_translation_key = "cancel_timer"

    def __init__(self, coordinator, key: str, number: int) -> None:
        super().__init__(coordinator, key, number, name_suffix="cancel")

    async def async_press(self) -> None:
        await self.coordinator.async_send(**{self._key: 0})
