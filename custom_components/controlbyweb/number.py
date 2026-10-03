"""Registers and analog outputs as number entities."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBWConfigEntry
from .const import (
    PREFIX_ANALOG_OUTPUT,
    PREFIX_REGISTER,
    indexed_keys,
    is_configured,
    to_float,
)
from .entity import CBWEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: CBWConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[CBWNumber] = []
    data = coordinator.data
    for key, n in indexed_keys(data, PREFIX_REGISTER):
        if is_configured(data[key]):  # unused registers are reported as "x.x"
            entities.append(CBWNumber(coordinator, key, f"Register {n}"))
    for key, n in indexed_keys(data, PREFIX_ANALOG_OUTPUT):
        if is_configured(data[key]):
            entities.append(CBWNumber(coordinator, key, f"Analog output {n}"))
    async_add_entities(entities)


class CBWNumber(CBWEntity, NumberEntity):
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = -1_000_000_000
    _attr_native_max_value = 1_000_000_000
    _attr_native_step = 0.01

    @property
    def native_value(self) -> float | None:
        return to_float(self._raw)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_send(**{self._key: value})
