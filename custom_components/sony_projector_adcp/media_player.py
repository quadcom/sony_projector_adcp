"""Media Player entity for Sony Projector ADCP."""
import asyncio
import logging
from typing import Any, Optional

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_platform import AddEntitiesCallback, async_get_current_platform
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    INPUT_SOURCES,
    PICTURE_MODES,
    POWER_STATUS_LABELS,
    READ_SETTINGS,
    label,
)
from .coordinator import SonyProjectorCoordinator
from .entity import device_info
from .protocol import SonyProjectorADCP

_LOGGER = logging.getLogger(__name__)

POWER_WATCH_INTERVAL = 1  # seconds
POWER_WATCH_TIMEOUT = 120  # seconds

# Service schemas
SERVICE_SEND_KEY = "send_key"
SERVICE_SET_PICTURE_MODE = "set_picture_mode"
SERVICE_SET_BRIGHTNESS = "set_brightness"
SERVICE_SET_CONTRAST = "set_contrast"
SERVICE_SET_SHARPNESS = "set_sharpness"
SERVICE_SET_LIGHT_OUTPUT = "set_light_output"
SERVICE_SEND_RAW_COMMAND = "send_raw_command"

ATTR_KEY = "key"
ATTR_MODE = "mode"
ATTR_VALUE = "value"
ATTR_COMMAND = "command"

KEY_COMMANDS = ["menu", "up", "down", "left", "right", "enter", "reset", "blank"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sony Projector media player."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities([SonyProjectorMediaPlayer(coordinator, config_entry)])
    
    # Register services
    platform = async_get_current_platform()
    
    platform.async_register_entity_service(
        SERVICE_SEND_KEY,
        {vol.Required(ATTR_KEY): vol.In(KEY_COMMANDS)},
        "async_send_key",
    )
    
    platform.async_register_entity_service(
        SERVICE_SET_PICTURE_MODE,
        {vol.Required(ATTR_MODE): vol.In(list(PICTURE_MODES.keys()))},
        "async_set_picture_mode_service",
    )
    
    platform.async_register_entity_service(
        SERVICE_SET_BRIGHTNESS,
        {vol.Required(ATTR_VALUE): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))},
        "async_set_brightness",
    )
    
    platform.async_register_entity_service(
        SERVICE_SET_CONTRAST,
        {vol.Required(ATTR_VALUE): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))},
        "async_set_contrast",
    )
    
    platform.async_register_entity_service(
        SERVICE_SET_SHARPNESS,
        {vol.Required(ATTR_VALUE): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))},
        "async_set_sharpness",
    )
    
    platform.async_register_entity_service(
        SERVICE_SET_LIGHT_OUTPUT,
        {vol.Required(ATTR_VALUE): vol.All(vol.Coerce(int), vol.Range(min=0, max=1000))},
        "async_set_light_output",
    )
    
    platform.async_register_entity_service(
        "increase_brightness",
        {},
        "async_increase_brightness",
    )
    
    platform.async_register_entity_service(
        "decrease_brightness",
        {},
        "async_decrease_brightness",
    )
    
    platform.async_register_entity_service(
        "increase_contrast",
        {},
        "async_increase_contrast",
    )
    
    platform.async_register_entity_service(
        "decrease_contrast",
        {},
        "async_decrease_contrast",
    )
    
    platform.async_register_entity_service(
        "increase_sharpness",
        {},
        "async_increase_sharpness",
    )
    
    platform.async_register_entity_service(
        "decrease_sharpness",
        {},
        "async_decrease_sharpness",
    )
    
    platform.async_register_entity_service(
        "increase_light_output",
        {},
        "async_increase_light_output",
    )
    
    platform.async_register_entity_service(
        "decrease_light_output",
        {},
        "async_decrease_light_output",
    )
    
    platform.async_register_entity_service(
        "set_reality_creation",
        {vol.Required("state"): vol.In(["on", "off"])},
        "async_set_reality_creation",
    )
    
    platform.async_register_entity_service(
        "toggle_reality_creation",
        {},
        "async_toggle_reality_creation",
    )
    
    platform.async_register_entity_service(
        SERVICE_SEND_RAW_COMMAND,
        {vol.Required(ATTR_COMMAND): str},
        "async_send_raw_command",
    )


class SonyProjectorMediaPlayer(
    CoordinatorEntity[SonyProjectorCoordinator], MediaPlayerEntity
):
    """Representation of a Sony Projector as a Media Player."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(
        self, coordinator: SonyProjectorCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_media_player"
        self._attr_device_info = device_info(entry)
        self._power_watch_task: Optional[asyncio.Task] = None

    @property
    def _projector(self) -> SonyProjectorADCP:
        """Return the projector connection."""
        return self.coordinator.projector

    @property
    def _values(self) -> dict[str, Any]:
        """Return the polled parameter values."""
        return self.coordinator.data.values

    @property
    def state(self) -> MediaPlayerState:
        """Return on while the projector is on or warming up."""
        return MediaPlayerState.ON if self.coordinator.is_on else MediaPlayerState.OFF

    async def async_turn_on(self) -> None:
        """Turn the projector on."""
        if await self._projector.set_power(True):
            self.coordinator.async_set_power_status("startup")
        self._start_power_watch()

    async def async_turn_off(self) -> None:
        """Turn the projector off."""
        if await self._projector.set_power(False):
            self.coordinator.async_set_power_status("cooling1")
        self._start_power_watch()

    def _start_power_watch(self) -> None:
        """(Re)start the background task that polls power status until it settles."""
        if self._power_watch_task and not self._power_watch_task.done():
            self._power_watch_task.cancel()
        self._power_watch_task = self.hass.async_create_background_task(
            self._power_watch(), f"{self.entity_id} power watch"
        )

    async def _power_watch(self) -> None:
        """Poll power status until it reaches a stable state or the timeout elapses."""
        for _ in range(POWER_WATCH_TIMEOUT // POWER_WATCH_INTERVAL):
            await asyncio.sleep(POWER_WATCH_INTERVAL)
            try:
                power_status = await self._projector.get_power_status(False)
            except Exception as e:
                _LOGGER.debug("Error polling power status: %s", e)
                continue
            if power_status:
                self.coordinator.async_set_power_status(power_status)
            if self.coordinator.data.power_status in ("on", "standby"):
                if self.coordinator.data.power_status == "on":
                    await self.coordinator.async_request_refresh()
                break

    async def async_will_remove_from_hass(self) -> None:
        """Cancel the power watch task if it is still running."""
        await super().async_will_remove_from_hass()
        if self._power_watch_task and not self._power_watch_task.done():
            self._power_watch_task.cancel()

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        source_key = None
        for key, name in INPUT_SOURCES.items():
            if name == source:
                source_key = key
                break

        if source_key and await self._projector.set_input(source_key):
            self.coordinator.async_update_values(input=source_key)

    async def async_send_key(self, key: str) -> None:
        """Send a remote control key command."""
        if await self._projector.send_key(key) and key == "blank":
            # The key toggles the picture blank, so read the new state back
            await self.coordinator.async_request_refresh()

    async def async_set_picture_mode_service(self, mode: str) -> None:
        """Set picture mode via service call."""
        if await self._projector.set_picture_mode(mode):
            self.coordinator.async_update_values(picture_mode=mode)
            # A new picture mode changes other settings and their options
            self.coordinator.mark_ranges_stale()
            await self.coordinator.async_request_refresh()

    async def _set_numeric(self, param: str, value: int) -> None:
        """Set a numeric parameter and publish it to every entity."""
        if await self._projector.set_numeric_value(param, value):
            self.coordinator.async_update_values(**{param: value})

    async def _step_numeric(self, param: str, step: int, maximum: int) -> None:
        """Move a numeric parameter by step within 0..maximum."""
        current = self._values.get(param)
        if current is None:
            current = 50
        await self._set_numeric(param, max(0, min(current + step, maximum)))

    async def async_set_brightness(self, value: int) -> None:
        """Set brightness via service call."""
        await self._set_numeric("brightness", value)

    async def async_set_contrast(self, value: int) -> None:
        """Set contrast via service call."""
        await self._set_numeric("contrast", value)

    async def async_set_sharpness(self, value: int) -> None:
        """Set sharpness via service call."""
        await self._set_numeric("sharpness", value)

    async def async_set_light_output(self, value: int) -> None:
        """Set light output via service call."""
        await self._set_numeric("light_output_val", value)

    async def async_increase_brightness(self) -> None:
        """Increase brightness by 1."""
        await self._step_numeric("brightness", 1, 100)

    async def async_decrease_brightness(self) -> None:
        """Decrease brightness by 1."""
        await self._step_numeric("brightness", -1, 100)

    async def async_increase_contrast(self) -> None:
        """Increase contrast by 1."""
        await self._step_numeric("contrast", 1, 100)

    async def async_decrease_contrast(self) -> None:
        """Decrease contrast by 1."""
        await self._step_numeric("contrast", -1, 100)

    async def async_increase_sharpness(self) -> None:
        """Increase sharpness by 1."""
        await self._step_numeric("sharpness", 1, 100)

    async def async_decrease_sharpness(self) -> None:
        """Decrease sharpness by 1."""
        await self._step_numeric("sharpness", -1, 100)

    async def async_increase_light_output(self) -> None:
        """Increase light output by 1."""
        await self._step_numeric("light_output_val", 1, 1000)

    async def async_decrease_light_output(self) -> None:
        """Decrease light output by 1."""
        await self._step_numeric("light_output_val", -1, 1000)

    async def async_set_reality_creation(self, state: str) -> None:
        """Set Reality Creation on or off."""
        success = await self._projector.set_reality_creation(state)
        if success:
            self.coordinator.async_update_values(real_cre=state)
        else:
            _LOGGER.error("Failed to set reality creation to %s", state)

    async def async_toggle_reality_creation(self) -> None:
        """Toggle Reality Creation on/off."""
        current = self._values.get("real_cre") or "off"
        new_state = "off" if current == "on" else "on"
        await self.async_set_reality_creation(new_state)

    async def async_send_raw_command(self, command: str) -> None:
        """Send a raw ADCP command to the projector."""
        response = await self._projector.send_command(command)
        if response:
            _LOGGER.info("Raw command '%s' returned: %s", command, response)
        else:
            _LOGGER.error("Raw command '%s' failed", command)

    @property
    def source(self) -> Optional[str]:
        """Return the current input source."""
        current = self._values.get("input")
        if current:
            return INPUT_SOURCES.get(current)
        return None

    @property
    def source_list(self) -> list[str]:
        """List of available input sources."""
        return list(INPUT_SOURCES.values())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        data = self.coordinator.data
        values = data.values
        attrs = {
            "video_muted": values.get("blank") == "on",
        }

        if data.power_status:
            attrs["power_status"] = POWER_STATUS_LABELS.get(
                data.power_status, data.power_status
            )

        if values.get("picture_mode"):
            attrs["picture_mode"] = PICTURE_MODES.get(
                values["picture_mode"], values["picture_mode"]
            )

        for attr, param in (
            ("brightness", "brightness"),
            ("contrast", "contrast"),
            ("sharpness", "sharpness"),
            ("light_output", "light_output_val"),
            ("reality_creation", "real_cre"),
        ):
            if values.get(param) is not None:
                attrs[attr] = values[param]

        for attr, param in READ_SETTINGS.items():
            value = values.get(param)
            if value is not None:
                # signal is already display text ("3840x2160/60p")
                attrs[attr] = value if attr == "signal" else label(value)
        attrs.update(data.hours)
        attrs.update(data.health)
        attrs.update(data.info)

        return attrs
