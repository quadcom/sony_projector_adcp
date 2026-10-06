"""Switch entities for Sony Projector ADCP."""
from typing import Any, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import SonyProjectorEntity

# ADCP parameter -> (name, icon)
SWITCHES = {
    "real_cre": ("Reality Creation", "mdi:auto-fix"),
    "input_lag_red": ("Input lag reduction", "mdi:timer-outline"),
    "blank": ("Picture blank", "mdi:projector-screen-off-outline"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the projector switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SonyProjectorSwitch(coordinator, entry, key, name, icon)
        for key, (name, icon) in SWITCHES.items()
    )


class SonyProjectorSwitch(SonyProjectorEntity, SwitchEntity):
    """A projector setting that is either "on" or "off"."""

    @property
    def available(self) -> bool:
        """Return True when the projector is on and reports the value."""
        return (
            super().available
            and self._value in ("on", "off")
            and self._range is not None
        )

    @property
    def is_on(self) -> Optional[bool]:
        """Return True when the setting is on."""
        value = self._value
        return value == "on" if value in ("on", "off") else None

    async def _set(self, state: str) -> None:
        """Set the value on the projector."""
        if not await self.coordinator.projector.set_value(self._key, state):
            raise HomeAssistantError(f"The projector did not accept {state}")
        self.coordinator.async_update_values(**{self._key: state})

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the setting on."""
        await self._set("on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the setting off."""
        await self._set("off")
