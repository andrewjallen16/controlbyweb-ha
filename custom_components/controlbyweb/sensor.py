"""Sensors: 1-Wire, analog inputs, frequency, counters, timers, Vin, registers."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfElectricPotential, UnitOfFrequency, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBWConfigEntry
from .const import (
    CONF_ONEWIRE_UNIT,
    CONF_WRITABLE_REGISTERS,
    KEY_FREQUENCY_INPUT,
    PREFIX_ANALOG_INPUT,
    PREFIX_COUNT,
    PREFIX_FREQUENCY,
    PREFIX_ON_TIME,
    PREFIX_ONE_WIRE,
    PREFIX_REGISTER,
    PREFIX_TOTAL_ON_TIME,
    UNIT_MAP,
    UNIT_NONE,
    indexed_keys,
    is_configured,
    parse_value,
    to_float,
    vin_keys,
)
from .entity import CBWEntity, async_setup_dynamic

DEG_F, DEG_C = "\u00b0F", "\u00b0C"


def _build(entry: CBWConfigEntry, coordinator) -> list[SensorEntity]:
    data = coordinator.data
    fallback = entry.options.get(CONF_ONEWIRE_UNIT, UNIT_NONE)
    fallback = None if fallback == UNIT_NONE else fallback
    entities: list[SensorEntity] = []

    for key, n in indexed_keys(data, PREFIX_ONE_WIRE):
        if is_configured(data[key]):  # empty 1-Wire slots are reported as "x.x"
            entities.append(CBWOneWireSensor(coordinator, key, n, fallback))
    for key, n in indexed_keys(data, PREFIX_ANALOG_INPUT):
        if is_configured(data[key]):
            entities.append(CBWSensor(coordinator, key, n, "analog_input"))
    if is_configured(data.get(KEY_FREQUENCY_INPUT)):
        entities.append(CBWSensor(coordinator, KEY_FREQUENCY_INPUT, None, "frequency_input"))

    vins = vin_keys(data)
    for key, n in vins:
        if len(vins) == 1:
            entities.append(CBWVinSensor(coordinator, key, None, "supply_voltage"))
        else:
            entities.append(CBWVinSensor(coordinator, key, n, "supply_voltage_n"))

    # Input functions (only present when assigned a Local I/O number on the device)
    for key, n in indexed_keys(data, PREFIX_FREQUENCY):
        entities.append(CBWFrequencySensor(coordinator, key, n, "input_frequency"))
    for key, n in indexed_keys(data, PREFIX_COUNT):
        entities.append(CBWCounterSensor(coordinator, key, n, "input_count"))
    for key, n in indexed_keys(data, PREFIX_ON_TIME):
        entities.append(CBWDurationSensor(coordinator, key, n, "input_on_time", False))
    for key, n in indexed_keys(data, PREFIX_TOTAL_ON_TIME):
        entities.append(CBWDurationSensor(coordinator, key, n, "input_total_on_time", True))

    # Registers are read-only here unless "Allow writing registers" is on
    # (then number.py provides them instead). On an X-404 they may hold Modbus readings.
    if not entry.options.get(CONF_WRITABLE_REGISTERS):
        for key, n in indexed_keys(data, PREFIX_REGISTER):
            if is_configured(data[key]):
                entities.append(CBWSensor(coordinator, key, n, "register"))
    return entities


async def async_setup_entry(
    hass: HomeAssistant, entry: CBWConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_dynamic(entry, async_add_entities, _build)


class CBWSensor(CBWEntity, SensorEntity):
    """Numeric value. A unit printed by the device (showUnits) is used when present."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _requires_value = True

    def __init__(self, coordinator, key: str, number: int | None, translation_key: str) -> None:
        super().__init__(coordinator, key, number)
        self._attr_translation_key = translation_key

    @property
    def native_value(self) -> float | None:
        return to_float(self._raw)

    @property
    def native_unit_of_measurement(self) -> str | None:
        _, unit = parse_value(self._raw)
        if unit:
            return UNIT_MAP.get(unit, unit)
        return self._attr_native_unit_of_measurement


class CBWOneWireSensor(CBWSensor):
    """Temperature/humidity probe. Unit comes from the device, else from the option."""

    def __init__(self, coordinator, key: str, number: int, fallback_unit: str | None) -> None:
        super().__init__(coordinator, key, number, "one_wire_sensor")
        self._attr_native_unit_of_measurement = fallback_unit

    @property
    def device_class(self) -> SensorDeviceClass | None:
        unit = self.native_unit_of_measurement
        if unit in (DEG_F, DEG_C):
            return SensorDeviceClass.TEMPERATURE
        if unit == "%":
            return SensorDeviceClass.HUMIDITY
        return None


class CBWVinSensor(CBWSensor):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT


class CBWFrequencySensor(CBWSensor):
    _attr_device_class = SensorDeviceClass.FREQUENCY
    _attr_native_unit_of_measurement = UnitOfFrequency.HERTZ


class CBWCounterSensor(CBWSensor):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 0


class CBWDurationSensor(CBWSensor):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator, key: str, number: int, translation_key: str, total: bool) -> None:
        super().__init__(coordinator, key, number, translation_key)
        self._attr_state_class = (
            SensorStateClass.TOTAL_INCREASING if total else SensorStateClass.MEASUREMENT
        )
