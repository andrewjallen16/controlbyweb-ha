"""Digital inputs and X-420 digital I/O."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBWConfigEntry
from .const import PREFIX_DIGITAL_INPUT, PREFIX_DIGITAL_IO, indexed_keys, to_float
from .entity import CBWEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: CBWConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[CBWDigital] = [
        CBWDigital(coordinator, key, f"Digital input {n}")
        for key, n in indexed_keys(coordinator.data, PREFIX_DIGITAL_INPUT)
    ]
    # X-420 digital I/O may be configured as input or output; shown read-only here.
    entities += [
        CBWDigital(coordinator, key, f"Digital I/O {n}")
        for key, n in indexed_keys(coordinator.data, PREFIX_DIGITAL_IO)
    ]
    async_add_entities(entities)


class CBWDigital(CBWEntity, BinarySensorEntity):
    @property
    def is_on(self) -> bool | None:
        value = to_float(self._raw)
        return None if value is None else value >= 1
