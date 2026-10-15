"""Writable registers (opt-in) and analog outputs as number entities."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBWConfigEntry
from .const import (
    CONF_WRITABLE_REGISTERS,
    PREFIX_ANALOG_OUTPUT,
    PREFIX_REGISTER,
    indexed_keys,
    is_configured,
    to_float,
)
from .entity import CBWEntity, async_setup_dynamic


def _build(entry: CBWConfigEntry, coordinator) -> list[CBWNumber]:
    data = coordinator.data
    entities: list[CBWNumber] = []
    if entry.options.get(CONF_WRITABLE_REGISTERS):
        for key, n in indexed_keys(data, PREFIX_REGISTER):
            if is_configured(data[key]):  # unused registers are reported as "x.x"
                entities.append(CBWNumber(coordinator, key, n, "register"))
    for key, n in indexed_keys(data, PREFIX_ANALOG_OUTPUT):
        if is_configured(data[key]):
            entities.append(CBWNumber(coordinator, key, n, "analog_output"))
    return entities


async def async_setup_entry(
    hass: HomeAssistant, entry: CBWConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_dynamic(entry, async_add_entities, _build)


class CBWNumber(CBWEntity, NumberEntity):
    _requires_value = True
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = -1_000_000_000
    _attr_native_max_value = 1_000_000_000
    _attr_native_step = 0.01

    def __init__(self, coordinator, key: str, number: int, translation_key: str) -> None:
        super().__init__(coordinator, key, number)
        self._attr_translation_key = translation_key

    @property
    def native_value(self) -> float | None:
        return to_float(self._raw)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_send(**{self._key: value})
