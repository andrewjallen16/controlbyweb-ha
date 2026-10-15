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
    CONF_FREQUENCY_UNIT,
    CONF_ONEWIRE_UNIT,
    CONF_WRITABLE_REGISTERS,
    PREFIX_ANALOG_INPUT,
    PREFIX_COUNT,
    PREFIX_FREQUENCY,
    PREFIX_ON_TIME,
    PREFIX_ONE_WIRE,
    PREFIX_REGISTER,
    PREFIX_TIMER,
    PREFIX_TOTAL_ON_TIME,
    SPEED_UNITS,
    UNIT_DEVICE_CLASS,
    UNIT_NONE,
    frequency_input_keys,
    indexed_keys,
    is_configured,
    normalize_unit,
    parse_value,
    to_float,
    vin_keys,
)
from .entity import CBWEntity, async_setup_dynamic
from .helpers import registered_keys

DEG_F, DEG_C = "\u00b0F", "\u00b0C"

_DEVICE_CLASSES = {
    "voltage": SensorDeviceClass.VOLTAGE,
    "current": SensorDeviceClass.CURRENT,
    "power": SensorDeviceClass.POWER,
    "apparent_power": SensorDeviceClass.APPARENT_POWER,
    "reactive_power": SensorDeviceClass.REACTIVE_POWER,
    "frequency": SensorDeviceClass.FREQUENCY,
    "energy": SensorDeviceClass.ENERGY,
    "temperature": SensorDeviceClass.TEMPERATURE,
}


def _build(entry: CBWConfigEntry, coordinator) -> list[SensorEntity]:
    data = coordinator.data
    # Keep an I/O's entity once it has been seen (unavailable while it reads "x.x")
    seen = registered_keys(coordinator.hass, entry, "sensor")

    def wanted(key: str) -> bool:
        return is_configured(data[key]) or key in seen

    one_wire_unit = entry.options.get(CONF_ONEWIRE_UNIT, UNIT_NONE)
    freq_unit = entry.options.get(CONF_FREQUENCY_UNIT, UNIT_NONE)
    entities: list[SensorEntity] = []

    for key, n in indexed_keys(data, PREFIX_ONE_WIRE):
        if wanted(key):
            entities.append(CBWOneWireSensor(coordinator, key, n, one_wire_unit))
    for key, n in indexed_keys(data, PREFIX_ANALOG_INPUT):
        if wanted(key):
            entities.append(CBWSensor(coordinator, key, n, "analog_input"))

    freq_keys = [(k, n) for k, n in frequency_input_keys(data) if wanted(k)]
    for key, n in freq_keys:
        if len(freq_keys) == 1:
            entities.append(CBWFrequencyInputSensor(coordinator, key, None, "frequency_input", freq_unit))
        else:
            entities.append(CBWFrequencyInputSensor(coordinator, key, n, "frequency_input_n", freq_unit))

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

    # Timers (down counters, 1 s resolution). Read-only; only present if the device
    # lists them in state.json under timerN.
    for key, n in indexed_keys(data, PREFIX_TIMER):
        entities.append(CBWDurationSensor(coordinator, key, n, "timer", False))

    # Registers are read-only here unless "Allow writing registers" is on
    # (then number.py provides them instead). On an X-404 they may hold Modbus readings.
    if not entry.options.get(CONF_WRITABLE_REGISTERS):
        for key, n in indexed_keys(data, PREFIX_REGISTER):
            if wanted(key):
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
            return normalize_unit(unit)
        # Defer to Home Assistant: reading self._attr_native_unit_of_measurement directly
        # raises AttributeError on sensors that never set it (unit-less registers,
        # analog inputs, counters), and the entity then never gets registered.
        return super().native_unit_of_measurement

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Fixed classes (supply voltage, durations...) win; otherwise derive it from the
        unit the device reports, e.g. "3.11 A" -> current, "47.57 W" -> power."""
        if (fixed := super().device_class) is not None:
            return fixed
        return _DEVICE_CLASSES.get(UNIT_DEVICE_CLASS.get(self.native_unit_of_measurement or ""))

    @property
    def state_class(self) -> SensorStateClass | None:
        if self.device_class == SensorDeviceClass.ENERGY:
            return SensorStateClass.TOTAL_INCREASING  # what Home Assistant expects for energy
        return super().state_class


class CBWOneWireSensor(CBWSensor):
    """Temperature/humidity probe. Unit comes from the device, else from the option."""

    def __init__(self, coordinator, key: str, number: int, fallback_unit: str) -> None:
        super().__init__(coordinator, key, number, "one_wire_sensor")
        self._attr_native_unit_of_measurement = (
            None if fallback_unit == UNIT_NONE else normalize_unit(fallback_unit)
        )

    @property
    def device_class(self) -> SensorDeviceClass | None:
        unit = self.native_unit_of_measurement
        if unit in (DEG_F, DEG_C):
            return SensorDeviceClass.TEMPERATURE
        if unit == "%":
            return SensorDeviceClass.HUMIDITY
        return None


class CBWFrequencyInputSensor(CBWSensor):
    """X-420 frequency input. With slope/offset set on the device it is a scaled value
    (e.g. wind speed from a magnetic anemometer). The unit comes from the device when
    it reports one, otherwise from the "Frequency input unit" option."""

    def __init__(
        self, coordinator, key: str, number: int | None, translation_key: str, fallback_unit: str
    ) -> None:
        super().__init__(coordinator, key, number, translation_key)
        self._attr_native_unit_of_measurement = (
            None if fallback_unit == UNIT_NONE else normalize_unit(fallback_unit)
        )

    @property
    def device_class(self) -> SensorDeviceClass | None:
        unit = self.native_unit_of_measurement
        if unit in SPEED_UNITS:
            return SensorDeviceClass.WIND_SPEED
        if unit == "Hz":
            return SensorDeviceClass.FREQUENCY
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
