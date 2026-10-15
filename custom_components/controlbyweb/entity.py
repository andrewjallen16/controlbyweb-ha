"""Base entity and dynamic entity creation."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MODEL, CONF_SSL, DOMAIN, MAC_RE, is_configured
from .coordinator import CBWCoordinator


class CBWEntity(CoordinatorEntity[CBWCoordinator]):
    """Entity bound to one key in the device state.

    Names come from translations ("Relay {number}"), or from the device's own I/O
    name when the "Use I/O names from the device" option is on and names matched.
    """

    _attr_has_entity_name = True
    _requires_value = False  # True: "x.x" (unreadable/unused) means unavailable

    def __init__(
        self,
        coordinator: CBWCoordinator,
        key: str,
        number: int | None = None,
        name_suffix: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        uid = entry.unique_id
        self._key = key
        self._attr_unique_id = f"{uid}_{key}"

        if custom := coordinator.custom_names.get(key):
            self._attr_name = f"{custom} {name_suffix}" if name_suffix else custom
        elif number is not None:
            self._attr_translation_placeholders = {"number": str(number)}

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
        if not super().available or self._key not in self.coordinator.data:
            return False
        return not self._requires_value or is_configured(self._raw)

    @property
    def _raw(self) -> Any:
        return self.coordinator.data.get(self._key)


def async_setup_dynamic(
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    build: Callable[[ConfigEntry, CBWCoordinator], list[Entity]],
) -> None:
    """Add entities now, and again whenever new keys appear in the device state.

    `build` returns entities for everything currently in the state; ones already
    added (matched by unique_id) are skipped, so a 1-Wire probe or I/O that is
    configured later shows up without reloading the integration.
    """
    coordinator: CBWCoordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _check() -> None:
        new = [e for e in build(entry, coordinator) if e.unique_id not in known]
        if new:
            known.update(e.unique_id for e in new)
            async_add_entities(new)

    _check()
    entry.async_on_unload(coordinator.async_add_listener(_check))
