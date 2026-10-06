"""Number entities for Sony Projector ADCP."""
from typing import Optional

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NUMBER_DEFAULT_RANGES
from .entity import SonyProjectorEntity

# ADCP parameter -> (name, icon)
NUMBERS = {
    "brightness": ("Brightness", "mdi:brightness-6"),
    "contrast": ("Contrast", "mdi:contrast-circle"),
    "sharpness": ("Sharpness", "mdi:image-filter-center-focus"),
    "color": ("Colour", "mdi:palette-outline"),
    "hue": ("Hue", "mdi:looks"),
    "light_output_val": ("Light output", "mdi:brightness-7"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the projector number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SonyProjectorNumber(coordinator, entry, key, name, icon)
        for key, (name, icon) in NUMBERS.items()
    )


class SonyProjectorNumber(SonyProjectorEntity, NumberEntity):
    """A numeric projector setting shown as a slider."""

    _attr_mode = NumberMode.SLIDER
    _attr_native_step = 1

    def _limit(self, edge: str) -> float:
        """Return the min or max the projector reported, or the default."""
        found = self._range
        if not isinstance(found, dict):
            found = NUMBER_DEFAULT_RANGES[self._key]
        return found[edge]

    @property
    def native_min_value(self) -> float:
        """Return the lowest accepted value."""
        return self._limit("min")

    @property
    def native_max_value(self) -> float:
        """Return the highest accepted value."""
        return self._limit("max")

    @property
    def available(self) -> bool:
        """Return True when the projector is on and the value is known."""
        return super().available and isinstance(self._value, int)

    @property
    def native_value(self) -> Optional[float]:
        """Return the current value."""
        value = self._value
        return value if isinstance(value, int) else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the value on the projector."""
        number = int(value)
        if not await self.coordinator.projector.set_value(self._key, number):
            raise HomeAssistantError(f"The projector did not accept {number}")
        self.coordinator.async_update_values(**{self._key: number})
