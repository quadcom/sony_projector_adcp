"""The Sony Projector ADCP integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_USE_AUTH, DEFAULT_PASSWORD, DEFAULT_USE_AUTH, DOMAIN
from .coordinator import SonyProjectorCoordinator
from .protocol import SonyProjectorADCP

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sony Projector ADCP from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    password = entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD)
    use_auth = entry.data.get(CONF_USE_AUTH, DEFAULT_USE_AUTH)

    projector = SonyProjectorADCP(host, port, password, use_auth)

    # Test connection
    if not await projector.connect():
        _LOGGER.error("Failed to connect to projector at %s:%s", host, port)
        return False

    await projector.disconnect()

    coordinator = SonyProjectorCoordinator(hass, entry, projector)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await projector.disconnect()
        raise

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.projector.disconnect()

    return unload_ok
