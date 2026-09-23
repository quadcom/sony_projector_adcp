"""Media Player entity for Sony Projector ADCP."""
import asyncio
import logging
import re
from typing import Any, Optional

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_platform import AddEntitiesCallback, async_get_current_platform
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .const import (
    DEFAULT_NAME,
    DOMAIN,
    INPUT_SOURCES,
    PICTURE_MODES,
    POWER_STATE_MAP,
    POWER_STATUS_LABELS,
    READ_SETTINGS,
)
from .protocol import SonyProjectorADCP

_LOGGER = logging.getLogger(__name__)


def _label(value: Any) -> Any:
    """Turn a raw ADCP value into a display label, e.g. "gamma7" -> "Gamma 7"."""
    if value is None or not isinstance(value, str):
        return value
    text = value.replace("_", " ")
    if re.fullmatch(r"d\d+", text):
        return text.upper()
    match = re.fullmatch(r"(.*?)(\d+)", text)
    if match and match.group(1):
        return f"{match.group(1).rstrip().title()} {match.group(2)}"
    return text.title()

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
    projector = hass.data[DOMAIN][config_entry.entry_id]
    name = config_entry.data.get(CONF_NAME, DEFAULT_NAME)
    
    async_add_entities([SonyProjectorMediaPlayer(projector, name, config_entry.entry_id)])
    
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
        {vol.Required(ATTR_VALUE): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))},
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


class SonyProjectorMediaPlayer(MediaPlayerEntity):
    """Representation of a Sony Projector as a Media Player."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(
        self, projector: SonyProjectorADCP, name: str, entry_id: str
    ) -> None:
        """Initialize the media player."""
        self._projector = projector
        self._attr_unique_id = f"{entry_id}_media_player"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": name,
            "manufacturer": "Sony",
            "model": "VPL-XW5000",
        }
        self._attr_state = MediaPlayerState.OFF
        self._power_status: Optional[str] = None
        self._power_watch_task: Optional[asyncio.Task] = None
        self._current_source = None
        self._is_blank = False
        self._picture_mode = None
        self._brightness = None
        self._contrast = None
        self._sharpness = None
        self._light_output = None
        self._reality_creation = None
        self._settings: dict[str, Any] = {}
        self._hours: dict[str, int] = {}
        self._health: dict[str, str] = {}
        self._info: dict[str, str] = {}

    async def _refresh_power(self) -> None:
        """Query the projector's power status and update state from it."""
        power_status = await self._projector.get_power_status()
        if power_status:
            self._power_status = power_status
            self._attr_state = (
                MediaPlayerState.ON
                if POWER_STATE_MAP.get(power_status) == "on"
                else MediaPlayerState.OFF
            )

    async def async_update(self) -> None:
        """Update the state of the projector."""
        try:
            await self._refresh_power()

            # Get additional info if powered on
            if self._attr_state == MediaPlayerState.ON:
                # Get input source
                try:
                    source = await self._projector.get_input()
                    if source:
                        self._current_source = source
                except Exception as e:
                    _LOGGER.debug("Error getting input source: %s", e)
                
                # Get blank status
                try:
                    blank_status = await self._projector.get_blank_status()
                    if blank_status is not None:
                        self._is_blank = blank_status
                except Exception as e:
                    _LOGGER.debug("Error getting blank status: %s", e)
                
                # Get picture mode - keep last value if query fails
                try:
                    picture_mode = await self._projector.get_picture_mode()
                    if picture_mode:
                        self._picture_mode = picture_mode
                except Exception as e:
                    _LOGGER.debug("Error getting picture mode: %s", e)
                
                # Get brightness - keep last value if query fails
                try:
                    brightness = await self._projector.get_numeric_value("brightness")
                    if brightness is not None:
                        self._brightness = brightness
                except Exception as e:
                    _LOGGER.debug("Error getting brightness: %s", e)
                
                # Get contrast - keep last value if query fails
                try:
                    contrast = await self._projector.get_numeric_value("contrast")
                    if contrast is not None:
                        self._contrast = contrast
                except Exception as e:
                    _LOGGER.debug("Error getting contrast: %s", e)
                
                # Get sharpness - keep last value if query fails
                try:
                    sharpness = await self._projector.get_numeric_value("sharpness")
                    if sharpness is not None:
                        self._sharpness = sharpness
                except Exception as e:
                    _LOGGER.debug("Error getting sharpness: %s", e)
                
                # Get light output - keep last value if query fails
                try:
                    light_output = await self._projector.get_numeric_value("light_output_val")
                    if light_output is not None:
                        self._light_output = light_output
                except Exception as e:
                    _LOGGER.debug("Error getting light output: %s", e)
                
                # Get reality creation - keep last value if query fails
                try:
                    reality_creation = await self._projector.get_reality_creation()
                    if reality_creation:
                        self._reality_creation = reality_creation
                except Exception as e:
                    _LOGGER.debug("Error getting reality creation: %s", e)

                # Get picture settings - keep last value if a query fails
                for attr, param in READ_SETTINGS.items():
                    try:
                        value = await self._projector.query(param)
                        if value is not None:
                            self._settings[attr] = value
                    except Exception as e:
                        _LOGGER.debug("Error getting %s: %s", attr, e)

                # Get operating hours
                try:
                    timer = await self._projector.query("timer")
                    if timer:
                        hours = {k: v for item in timer for k, v in item.items()}
                        if "operation" in hours:
                            self._hours["operating_hours"] = hours["operation"]
                        if "light_src" in hours:
                            self._hours["light_source_hours"] = hours["light_src"]
                except Exception as e:
                    _LOGGER.debug("Error getting timer: %s", e)

                # Get error and warning status
                try:
                    errors = await self._projector.query("error")
                    if errors is not None:
                        active = [e for e in errors if e != "no_err"]
                        self._health["error"] = (
                            "None" if not active else ", ".join(_label(e) for e in active)
                        )
                except Exception as e:
                    _LOGGER.debug("Error getting error status: %s", e)

                try:
                    warnings = await self._projector.query("warning")
                    if warnings is not None:
                        active = [w for w in warnings if w != "no_warn"]
                        self._health["warning"] = (
                            "None" if not active else ", ".join(_label(w) for w in active)
                        )
                except Exception as e:
                    _LOGGER.debug("Error getting warning status: %s", e)

                # Model / serial / firmware - queried once per HA start
                if not self._info:
                    try:
                        model = await self._projector.query("modelname")
                        if model is not None:
                            self._info["model"] = model
                        serial = await self._projector.query("serialnum")
                        if serial is not None:
                            self._info["serial"] = serial
                        version = await self._projector.query("version")
                        if version:
                            firmware = {k: v for item in version for k, v in item.items()}
                            if "main" in firmware:
                                self._info["firmware"] = firmware["main"]
                            if "laser" in firmware:
                                self._info["laser_firmware"] = firmware["laser"]
                    except Exception as e:
                        _LOGGER.debug("Error getting device info: %s", e)
            else:
                # If powered off, clear these values
                self._brightness = None
                self._contrast = None
                self._sharpness = None
                self._light_output = None
                self._picture_mode = None
                self._reality_creation = None
                self._settings = {}
                self._health = {}
                    
        except Exception as e:
            _LOGGER.error("Error updating projector state: %s", e)
            self._attr_available = False
            return
        
        self._attr_available = True

    async def async_turn_on(self) -> None:
        """Turn the projector on."""
        if await self._projector.set_power(True):
            self._attr_state = MediaPlayerState.ON
            self._power_status = "startup"
            self.async_write_ha_state()
        self._start_power_watch()

    async def async_turn_off(self) -> None:
        """Turn the projector off."""
        if await self._projector.set_power(False):
            self._attr_state = MediaPlayerState.OFF
            self._power_status = "cooling1"
            self.async_write_ha_state()
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
                await self._refresh_power()
            except Exception as e:
                _LOGGER.debug("Error polling power status: %s", e)
                continue
            self.async_write_ha_state()
            if self._power_status in ("on", "standby"):
                break

    async def async_will_remove_from_hass(self) -> None:
        """Cancel the power watch task if it is still running."""
        if self._power_watch_task and not self._power_watch_task.done():
            self._power_watch_task.cancel()

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        source_key = None
        for key, name in INPUT_SOURCES.items():
            if name == source:
                source_key = key
                break
        
        if source_key:
            await self._projector.set_input(source_key)
            self._current_source = source_key

    async def async_send_key(self, key: str) -> None:
        """Send a remote control key command."""
        await self._projector.send_key(key)

    async def async_set_picture_mode_service(self, mode: str) -> None:
        """Set picture mode via service call."""
        await self._projector.set_picture_mode(mode)
        self._picture_mode = mode

    async def async_set_brightness(self, value: int) -> None:
        """Set brightness via service call."""
        await self._projector.set_numeric_value("brightness", value)
        self._brightness = value

    async def async_set_contrast(self, value: int) -> None:
        """Set contrast via service call."""
        await self._projector.set_numeric_value("contrast", value)
        self._contrast = value

    async def async_set_sharpness(self, value: int) -> None:
        """Set sharpness via service call."""
        await self._projector.set_numeric_value("sharpness", value)
        self._sharpness = value

    async def async_set_light_output(self, value: int) -> None:
        """Set light output via service call."""
        await self._projector.set_numeric_value("light_output_val", value)
        self._light_output = value

    async def async_increase_brightness(self) -> None:
        """Increase brightness by 1."""
        current = self._brightness if self._brightness is not None else 50
        new_value = min(current + 1, 100)
        await self._projector.set_numeric_value("brightness", new_value)
        self._brightness = new_value

    async def async_decrease_brightness(self) -> None:
        """Decrease brightness by 1."""
        current = self._brightness if self._brightness is not None else 50
        new_value = max(current - 1, 0)
        await self._projector.set_numeric_value("brightness", new_value)
        self._brightness = new_value

    async def async_increase_contrast(self) -> None:
        """Increase contrast by 1."""
        current = self._contrast if self._contrast is not None else 50
        new_value = min(current + 1, 100)
        await self._projector.set_numeric_value("contrast", new_value)
        self._contrast = new_value

    async def async_decrease_contrast(self) -> None:
        """Decrease contrast by 1."""
        current = self._contrast if self._contrast is not None else 50
        new_value = max(current - 1, 0)
        await self._projector.set_numeric_value("contrast", new_value)
        self._contrast = new_value

    async def async_increase_sharpness(self) -> None:
        """Increase sharpness by 1."""
        current = self._sharpness if self._sharpness is not None else 50
        new_value = min(current + 1, 100)
        await self._projector.set_numeric_value("sharpness", new_value)
        self._sharpness = new_value

    async def async_decrease_sharpness(self) -> None:
        """Decrease sharpness by 1."""
        current = self._sharpness if self._sharpness is not None else 50
        new_value = max(current - 1, 0)
        await self._projector.set_numeric_value("sharpness", new_value)
        self._sharpness = new_value

    async def async_increase_light_output(self) -> None:
        """Increase light output by 1."""
        current = self._light_output if self._light_output is not None else 50
        new_value = min(current + 1, 100)
        await self._projector.set_numeric_value("light_output_val", new_value)
        self._light_output = new_value

    async def async_decrease_light_output(self) -> None:
        """Decrease light output by 1."""
        current = self._light_output if self._light_output is not None else 50
        new_value = max(current - 1, 0)
        await self._projector.set_numeric_value("light_output_val", new_value)
        self._light_output = new_value

    async def async_set_reality_creation(self, state: str) -> None:
        """Set Reality Creation on or off."""
        success = await self._projector.set_reality_creation(state)
        if success:
            self._reality_creation = state
        else:
            _LOGGER.error("Failed to set reality creation to %s", state)

    async def async_toggle_reality_creation(self) -> None:
        """Toggle Reality Creation on/off."""
        current = self._reality_creation if self._reality_creation else "off"
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
        if self._current_source:
            return INPUT_SOURCES.get(self._current_source)
        return None

    @property
    def source_list(self) -> list[str]:
        """List of available input sources."""
        return list(INPUT_SOURCES.values())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {
            "video_muted": self._is_blank,
        }

        if self._power_status:
            attrs["power_status"] = POWER_STATUS_LABELS.get(self._power_status, self._power_status)

        if self._picture_mode:
            attrs["picture_mode"] = PICTURE_MODES.get(self._picture_mode, self._picture_mode)
        
        if self._brightness is not None:
            attrs["brightness"] = self._brightness
        
        if self._contrast is not None:
            attrs["contrast"] = self._contrast
        
        if self._sharpness is not None:
            attrs["sharpness"] = self._sharpness
        
        if self._light_output is not None:
            attrs["light_output"] = self._light_output
        
        if self._reality_creation is not None:
            attrs["reality_creation"] = self._reality_creation

        for key, value in self._settings.items():
            attrs[key] = _label(value)
        attrs.update(self._hours)
        attrs.update(self._health)
        attrs.update(self._info)

        return attrs