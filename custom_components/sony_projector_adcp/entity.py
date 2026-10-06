"""Base entity for the Sony Projector ADCP platforms."""
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import SonyProjectorCoordinator


def device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return the device every entity of this projector belongs to."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_NAME, DEFAULT_NAME),
        manufacturer="Sony",
        model="VPL-XW5000",
    )


class SonyProjectorEntity(CoordinatorEntity[SonyProjectorCoordinator]):
    """A settings entity that is available only while the projector is on."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SonyProjectorCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = device_info(entry)

    @property
    def _value(self) -> Any:
        """Current raw value of this entity's parameter, or None."""
        return self.coordinator.data.values.get(self._key)

    @property
    def _range(self) -> Any:
        """Accepted values of this entity's parameter right now, or None."""
        return self.coordinator.data.ranges.get(self._key)

    @property
    def available(self) -> bool:
        """Return True while the projector is reachable and on."""
        return super().available and self.coordinator.is_on
