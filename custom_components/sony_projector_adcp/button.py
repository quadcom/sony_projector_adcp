"""Button entities for Sony Projector ADCP."""
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import SonyProjectorEntity

# remote key -> (name, icon)
BUTTONS = {
    "menu": ("Menu", "mdi:menu"),
    "up": ("Up", "mdi:chevron-up"),
    "down": ("Down", "mdi:chevron-down"),
    "left": ("Left", "mdi:chevron-left"),
    "right": ("Right", "mdi:chevron-right"),
    "enter": ("Enter", "mdi:keyboard-return"),
    "reset": ("Reset", "mdi:restore"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the projector remote key buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SonyProjectorButton(coordinator, entry, key, name, icon)
        for key, (name, icon) in BUTTONS.items()
    )


class SonyProjectorButton(SonyProjectorEntity, ButtonEntity):
    """A remote control key."""

    async def async_press(self) -> None:
        """Send the key to the projector."""
        if not await self.coordinator.projector.send_key(self._key):
            raise HomeAssistantError(f"The projector did not accept key {self._key}")
