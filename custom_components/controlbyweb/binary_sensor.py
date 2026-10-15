"""Digital inputs and X-420 digital I/O."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBWConfigEntry
from .const import PREFIX_DIGITAL_INPUT, PREFIX_DIGITAL_IO, indexed_keys, to_float
from .entity import CBWEntity, async_setup_dynamic


def _build(entry: CBWConfigEntry, coordinator) -> list[CBWDigital]:
    data = coordinator.data
    entities = [
        CBWDigital(coordinator, key, n, "digital_input")
        for key, n in indexed_keys(data, PREFIX_DIGITAL_INPUT)
    ]
    # X-420 digital I/O may be configured as input or output; shown read-only here.
    entities += [
        CBWDigital(coordinator, key, n, "digital_io")
        for key, n in indexed_keys(data, PREFIX_DIGITAL_IO)
    ]
    return entities


async def async_setup_entry(
    hass: HomeAssistant, entry: CBWConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_dynamic(entry, async_add_entities, _build)


class CBWDigital(CBWEntity, BinarySensorEntity):
    def __init__(self, coordinator, key: str, number: int, translation_key: str) -> None:
        super().__init__(coordinator, key, number)
        self._attr_translation_key = translation_key

    @property
    def is_on(self) -> bool | None:
        value = to_float(self._raw)
        return None if value is None else value >= 1
