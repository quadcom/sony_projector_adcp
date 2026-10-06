"""Data update coordinator for Sony Projector ADCP."""
from dataclasses import dataclass, field, replace
from datetime import timedelta
import logging
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    NUMBER_DEFAULT_RANGES,
    POWER_STATE_MAP,
    READ_SETTINGS,
    SCAN_INTERVAL,
    SELECT_PARAMS,
    SWITCH_PARAMS,
    label,
)
from .protocol import SonyProjectorADCP

_LOGGER = logging.getLogger(__name__)

# Numeric parameters polled with a plain integer reply
NUMERIC_PARAMS = ("brightness", "contrast", "sharpness", "light_output_val")

# String parameters polled besides the READ_SETTINGS ones
STRING_PARAMS = ("input", "blank", "picture_mode", "real_cre")

# Values cleared when the projector is not on
CLEARED_WHEN_OFF = (
    *NUMERIC_PARAMS,
    "picture_mode",
    "real_cre",
    *READ_SETTINGS.values(),
)


@dataclass
class SonyProjectorData:
    """Everything polled from the projector.

    values holds the current value of each ADCP parameter by name (input,
    blank "on"/"off", picture_mode, the numeric and string settings and
    signal). ranges holds, per parameter, the list of accepted strings, a
    {"min", "max"} dict, or None when the projector reports none.
    """

    power_status: Optional[str] = None
    values: dict[str, Any] = field(default_factory=dict)
    hours: dict[str, int] = field(default_factory=dict)
    health: dict[str, str] = field(default_factory=dict)
    info: dict[str, str] = field(default_factory=dict)
    ranges: dict[str, Any] = field(default_factory=dict)


class SonyProjectorCoordinator(DataUpdateCoordinator[SonyProjectorData]):
    """Poll the projector and share the result with every entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        projector: SonyProjectorADCP,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self.projector = projector
        self._range_key: Optional[tuple] = None
        self._ranges_stale = False
        self._number_ranges_read = False

    @property
    def is_on(self) -> bool:
        """Return True when the projector is on or warming up."""
        return (
            self.data is not None
            and POWER_STATE_MAP.get(self.data.power_status) == "on"
        )

    @callback
    def async_set_power_status(self, power_status: str) -> None:
        """Publish a new raw power status to every entity."""
        if self.data is not None:
            self.async_set_updated_data(replace(self.data, power_status=power_status))

    @callback
    def async_update_values(self, **values: Any) -> None:
        """Publish changed parameter values to every entity."""
        if self.data is not None:
            self.async_set_updated_data(
                replace(self.data, values={**self.data.values, **values})
            )

    @callback
    def mark_ranges_stale(self) -> None:
        """Re-read the option lists on the next poll."""
        self._ranges_stale = True

    async def _async_update_data(self) -> SonyProjectorData:
        """Poll the projector."""
        previous = self.data or SonyProjectorData()
        try:
            power_status = await self.projector.get_power_status()
        except Exception as err:
            raise UpdateFailed(f"Error reading power status: {err}") from err
        if not power_status:
            raise UpdateFailed("Projector did not report its power status")

        data = replace(
            previous,
            power_status=power_status,
            values=dict(previous.values),
            hours=dict(previous.hours),
            health=dict(previous.health),
            info=dict(previous.info),
            ranges=dict(previous.ranges),
        )

        if POWER_STATE_MAP.get(power_status) == "on":
            await self._poll_values(data)
            await self._poll_status(data)
            if power_status == "on":
                await self._poll_ranges(data)
        else:
            for key in CLEARED_WHEN_OFF:
                data.values.pop(key, None)
            data.health = {}
            self._range_key = None

        return data

    async def _poll_values(self, data: SonyProjectorData) -> None:
        """Read current values - keep the last value if a query fails."""
        projector = self.projector
        for param in STRING_PARAMS:
            try:
                value = await projector.query(param, False)
                if isinstance(value, str) and value:
                    data.values[param] = value
            except Exception as e:
                _LOGGER.debug("Error getting %s: %s", param, e)

        for param in NUMERIC_PARAMS:
            try:
                value = await projector.get_numeric_value(param, False)
                if value is not None:
                    data.values[param] = value
            except Exception as e:
                _LOGGER.debug("Error getting %s: %s", param, e)

        for param in READ_SETTINGS.values():
            try:
                value = await projector.query(param, False)
                if value is not None:
                    data.values[param] = value
            except Exception as e:
                _LOGGER.debug("Error getting %s: %s", param, e)

    async def _poll_status(self, data: SonyProjectorData) -> None:
        """Read hours, error and warning status, and the once-per-start info."""
        projector = self.projector

        try:
            timer = await projector.query("timer", False)
            if timer:
                hours = {k: v for item in timer for k, v in item.items()}
                if "operation" in hours:
                    data.hours["operating_hours"] = hours["operation"]
                if "light_src" in hours:
                    data.hours["light_source_hours"] = hours["light_src"]
        except Exception as e:
            _LOGGER.debug("Error getting timer: %s", e)

        try:
            errors = await projector.query("error", False)
            if errors is not None:
                active = [e for e in errors if e != "no_err"]
                data.health["error"] = (
                    "None" if not active else ", ".join(label(e) for e in active)
                )
        except Exception as e:
            _LOGGER.debug("Error getting error status: %s", e)

        try:
            warnings = await projector.query("warning", False)
            if warnings is not None:
                active = [w for w in warnings if w != "no_warn"]
                data.health["warning"] = (
                    "None" if not active else ", ".join(label(w) for w in active)
                )
        except Exception as e:
            _LOGGER.debug("Error getting warning status: %s", e)

        # Model / serial / firmware - queried once per HA start
        if not data.info:
            try:
                model = await projector.query("modelname", False)
                if model is not None:
                    data.info["model"] = model
                serial = await projector.query("serialnum", False)
                if serial is not None:
                    data.info["serial"] = serial
                version = await projector.query("version", False)
                if version:
                    firmware = {k: v for item in version for k, v in item.items()}
                    if "main" in firmware:
                        data.info["firmware"] = firmware["main"]
                    if "laser" in firmware:
                        data.info["laser_firmware"] = firmware["laser"]
            except Exception as e:
                _LOGGER.debug("Error getting device info: %s", e)

    async def _poll_ranges(self, data: SonyProjectorData) -> None:
        """Read the option lists and number ranges the projector accepts now.

        Option lists depend on picture mode, signal and HDR mode, so they are
        read again when any of those changes or after a set from an entity.
        Number ranges are read once per start.
        """
        range_key = (
            data.values.get("picture_mode"),
            data.values.get("signal"),
            data.values.get("hdr"),
        )
        if self._ranges_stale or range_key != self._range_key:
            for param in (*SELECT_PARAMS, *SWITCH_PARAMS):
                try:
                    data.ranges[param] = await self.projector.query_range(param)
                except Exception as e:
                    _LOGGER.debug("Error getting range of %s: %s", param, e)
                    data.ranges[param] = None
            self._range_key = range_key
            self._ranges_stale = False

        if not self._number_ranges_read:
            for param, default in NUMBER_DEFAULT_RANGES.items():
                try:
                    found = await self.projector.query_range(param)
                except Exception as e:
                    _LOGGER.debug("Error getting range of %s: %s", param, e)
                    found = None
                data.ranges[param] = found if isinstance(found, dict) else default
            self._number_ranges_read = True
