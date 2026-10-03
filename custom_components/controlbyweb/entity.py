"""Base entity."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SSL, DOMAIN
from .coordinator import CBWCoordinator
from homeassistant.const import CONF_HOST, CONF_PORT


class CBWEntity(CoordinatorEntity[CBWCoordinator]):
    """Entity bound to one key in state.json."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CBWCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        scheme = "https" if entry.data.get(CONF_SSL) else "http"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=f"ControlByWeb {entry.data[CONF_HOST]}",
            manufacturer="ControlByWeb (Xytronix)",
            model="400 Series",
            configuration_url=f"{scheme}://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}/setup.html",
        )

    @property
    def available(self) -> bool:
        return super().available and self._key in self.coordinator.data

    @property
    def _raw(self):
        return self.coordinator.data.get(self._key)
