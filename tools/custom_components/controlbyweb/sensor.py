"""Sensors: 1-Wire, analog inputs, frequency, counters, timers, Vin, reboot status."""
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
    KEY_FREQUENCY_INPUT,
    KEY_REBOOT_STATE,
    KEY_TOTAL_REBOOTS,
    PREFIX_ANALOG_INPUT,
    PREFIX_COUNT,
    PREFIX_FREQUENCY,
    PREFIX_ON_TIME,
    PREFIX_ONE_WIRE,
    PREFIX_TOTAL_ON_TIME,
    REBOOT_STATES,
    UNIT_MAP,
    UNIT_NONE,
    indexed_keys,
    is_configured,
    parse_value,
    to_float,
    vin_keys,
)
from .entity import CBWEntity

DEG_F, DEG_C = "\u00b0F", "\u00b0C"


async def async_setup_entry(
    hass: HomeAssistant, entry: CBWConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data
    fallback = entry.options.get(CONF_ONEWIRE_UNIT, UNIT_NONE)
    fallback = None if fallback == UNIT_NONE else fallback
    entities: list[SensorEntity] = []

    for key, n in indexed_keys(data, PREFIX_ONE_WIRE):
        if is_configured(data[key]):  # empty 1-Wire slots are reported as "x.x"
            entities.append(CBWOneWireSensor(coordinator, key, f"1-Wire sensor {n}", fallback))
    for key, n in indexed_keys(data, PREFIX_ANALOG_INPUT):
        if is_configured(data[key]):
            entities.append(CBWSensor(coordinator, key, f"Analog input {n}"))
    if is_configured(data.get(KEY_FREQUENCY_INPUT)):
        entities.append(CBWSensor(coordinator, KEY_FREQUENCY_INPUT, "Frequency input"))

    vins = vin_keys(data)
    for key, n in vins:
        name = "Supply voltage" if len(vins) == 1 else f"Supply voltage {n}"
        entities.append(CBWVinSensor(coordinator, key, name))

    # Input functions (only present when assigned a Local Number on the device)
    for key, n in indexed_keys(data, PREFIX_FREQUENCY):
        entities.append(CBWFrequencySensor(coordinator, key, f"Input {n} frequency"))
    for key, n in indexed_keys(data, PREFIX_COUNT):
        entities.append(CBWCounterSensor(coordinator, key, f"Input {n} count"))
    for key, n in indexed_keys(data, PREFIX_ON_TIME):
        entities.append(CBWDurationSensor(coordinator, key, f"Input {n} on time", False))
    for key, n in indexed_keys(data, PREFIX_TOTAL_ON_TIME):
        entities.append(CBWDurationSensor(coordinator, key, f"Input {n} total on time", True))

    # Legacy WebRelay in Automatic Reboot mode
    if KEY_REBOOT_STATE in data:
        entities.append(CBWRebootStateSensor(coordinator, KEY_REBOOT_STATE, "Reboot state"))
    if KEY_TOTAL_REBOOTS in data:
        entities.append(CBWCounterSensor(coordinator, KEY_TOTAL_REBOOTS, "Total reboots"))

    async_add_entities(entities)


class CBWSensor(CBWEntity, SensorEntity):
    """Numeric value. A unit printed by the device (showUnits) is used when present."""

    _attr_state_class = SensorStateClass.MEASUREMENT

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

    def __init__(self, coordinator, key, name, fallback_unit: str | None) -> None:
        super().__init__(coordinator, key, name)
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

    def __init__(self, coordinator, key, name, total: bool) -> None:
        super().__init__(coordinator, key, name)
        self._attr_state_class = (
            SensorStateClass.TOTAL_INCREASING if total else SensorStateClass.MEASUREMENT
        )


class CBWRebootStateSensor(CBWEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(REBOOT_STATES.values())

    @property
    def native_value(self) -> str | None:
        value = to_float(self._raw)
        return None if value is None else REBOOT_STATES.get(int(value))
