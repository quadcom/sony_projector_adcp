"""Select entities for Sony Projector ADCP."""
from typing import Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, option_label
from .entity import SonyProjectorEntity

# ADCP parameter -> (name, icon)
SELECTS = {
    "picture_mode": ("Picture mode", "mdi:image-filter-hdr"),
    "input": ("Input", "mdi:video-input-hdmi"),
    "color_temp": ("Colour temperature", "mdi:thermometer"),
    "color_space": ("Colour space", "mdi:palette"),
    "gamma_correction": ("Gamma", "mdi:gamma"),
    "motionflow": ("Motionflow", "mdi:motion-play-outline"),
    "contrast_enh": ("Contrast enhancer", "mdi:contrast-box"),
    "nr": ("Noise reduction", "mdi:blur"),
    "hdr": ("HDR", "mdi:hdr"),
    "aspect": ("Aspect", "mdi:aspect-ratio"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the projector select entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SonyProjectorSelect(coordinator, entry, key, name, icon)
        for key, (name, icon) in SELECTS.items()
    )


class SonyProjectorSelect(SonyProjectorEntity, SelectEntity):
    """A projector setting chosen from the options the projector accepts now."""

    def _raw_options(self) -> list[str]:
        """Accepted raw values in the projector's order, plus the current one."""
        options = list(self._range) if isinstance(self._range, list) else []
        value = self._value
        if options and isinstance(value, str) and value not in options:
            options.append(value)
        return options

    @property
    def available(self) -> bool:
        """Return True when the projector is on and offers options."""
        return (
            super().available
            and isinstance(self._value, str)
            and bool(self._raw_options())
        )

    @property
    def options(self) -> list[str]:
        """Return the labels of the options the projector accepts now."""
        return [option_label(self._key, raw) for raw in self._raw_options()]

    @property
    def current_option(self) -> Optional[str]:
        """Return the label of the current value."""
        value = self._value
        return option_label(self._key, value) if isinstance(value, str) else None

    async def async_select_option(self, option: str) -> None:
        """Set the projector to the chosen option."""
        raw = next(
            (r for r in self._raw_options() if option_label(self._key, r) == option),
            None,
        )
        if raw is None:
            raise HomeAssistantError(f"{option} is not available for {self.name}")
        if not await self.coordinator.projector.set_value(self._key, raw):
            raise HomeAssistantError(f"The projector did not accept {option}")
        self.coordinator.async_update_values(**{self._key: raw})
        self.coordinator.mark_ranges_stale()
        await self.coordinator.async_request_refresh()
