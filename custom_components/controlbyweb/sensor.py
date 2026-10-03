"""1-Wire sensors, analog inputs and Vin."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfElectricPotential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBWConfigEntry
from .const import (
    KEY_VIN,
    PREFIX_ANALOG_INPUT,
    PREFIX_ONE_WIRE,
    indexed_keys,
    to_float,
)
from .entity import CBWEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: CBWConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[CBWSensor] = []
    for key, n in indexed_keys(coordinator.data, PREFIX_ONE_WIRE):
        entities.append(CBWSensor(coordinator, key, f"1-Wire sensor {n}"))
    for key, n in indexed_keys(coordinator.data, PREFIX_ANALOG_INPUT):
        entities.append(CBWSensor(coordinator, key, f"Analog input {n}"))
    if KEY_VIN in coordinator.data:
        entities.append(CBWVinSensor(coordinator, KEY_VIN, "Supply voltage"))
    async_add_entities(entities)


class CBWSensor(CBWEntity, SensorEntity):
    """Unit is whatever the device is configured to report (set in its I/O setup)."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        return to_float(self._raw)


class CBWVinSensor(CBWSensor):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
