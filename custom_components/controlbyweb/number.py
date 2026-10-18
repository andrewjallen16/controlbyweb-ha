"""Writable registers (opt-in) and analog outputs as number entities."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBWConfigEntry
from .const import (
    CONF_WRITABLE_REGISTERS,
    MAX_TIMER,
    PREFIX_ANALOG_OUTPUT,
    PREFIX_REGISTER,
    PREFIX_TIMER,
    indexed_keys,
    is_configured,
    to_float,
)
from .entity import CBWEntity, async_setup_dynamic
from .helpers import registered_keys


def _build(entry: CBWConfigEntry, coordinator) -> list[CBWNumber]:
    data = coordinator.data
    seen = registered_keys(coordinator.hass, entry, "number")  # keep once-seen I/O
    entities: list[CBWNumber] = []
    if entry.options.get(CONF_WRITABLE_REGISTERS):
        for key, n in indexed_keys(data, PREFIX_REGISTER):
            if is_configured(data[key]) or key in seen:  # unused registers read "x.x"
                entities.append(CBWNumber(coordinator, key, n, "register"))
    for key, n in indexed_keys(data, PREFIX_ANALOG_OUTPUT):
        if is_configured(data[key]) or key in seen:
            entities.append(CBWNumber(coordinator, key, n, "analog_output"))
    # A box to type a timer's seconds into (starts it); needs no option, unlike registers
    for key, n in indexed_keys(data, PREFIX_TIMER):
        entities.append(CBWTimerNumber(coordinator, key, n))
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

    def __init__(
        self, coordinator, key: str, number: int, translation_key: str, name_suffix: str | None = None
    ) -> None:
        super().__init__(coordinator, key, number, name_suffix=name_suffix)
        self._attr_translation_key = translation_key

    @property
    def native_value(self) -> float | None:
        return to_float(self._raw)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_send(**{self._key: value})


class CBWTimerNumber(CBWNumber):
    """Type a number of seconds to start (or restart) a timer; it shows the time left while the
    timer runs, and 0 stops it. Starting a timer with state.json?timer1=30 was confirmed on an
    X-420; the module counts down, so the box value falls by itself."""

    _attr_native_min_value = 0
    _attr_native_max_value = MAX_TIMER
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator, key: str, number: int) -> None:
        super().__init__(coordinator, key, number, "timer_set", name_suffix="set")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_send(**{self._key: int(value)})
