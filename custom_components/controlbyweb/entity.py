"""Base entity."""
from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MODEL, CONF_SSL, DOMAIN, MAC_RE
from .coordinator import CBWCoordinator


class CBWEntity(CoordinatorEntity[CBWCoordinator]):
    """Entity bound to one key in the device state."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CBWCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        uid = entry.unique_id
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{uid}_{key}"

        model = entry.options.get(CONF_MODEL) or entry.data.get(CONF_MODEL) or "400 Series"
        scheme = "https" if entry.data.get(CONF_SSL) else "http"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            connections={(CONNECTION_NETWORK_MAC, uid.lower())} if MAC_RE.match(uid) else set(),
            name=f"ControlByWeb {model} ({entry.data[CONF_HOST]})",
            manufacturer="ControlByWeb (Xytronix)",
            model=model,
            configuration_url=f"{scheme}://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}/setup.html",
        )

    @property
    def available(self) -> bool:
        return super().available and self._key in self.coordinator.data

    @property
    def _raw(self):
        return self.coordinator.data.get(self._key)
