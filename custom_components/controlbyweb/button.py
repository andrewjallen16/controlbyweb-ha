"""Relay pulse buttons."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBWConfigEntry
from .const import PREFIX_RELAY, RELAY_PULSE, indexed_keys
from .entity import CBWEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: CBWConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        CBWPulseButton(coordinator, key, f"Relay {n} pulse")
        for key, n in indexed_keys(coordinator.data, PREFIX_RELAY)
    )


class CBWPulseButton(CBWEntity, ButtonEntity):
    """Pulses the relay for the Pulse Time set in the device's I/O setup."""

    async def async_press(self) -> None:
        await self.coordinator.async_send(**{self._key: RELAY_PULSE})
