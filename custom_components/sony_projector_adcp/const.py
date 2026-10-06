"""Constants for Sony Projector ADCP integration."""
import re
from typing import Any

DOMAIN = "sony_projector_adcp"

# Configuration
CONF_HOST = "host"
CONF_PORT = "port"
CONF_PASSWORD = "password"
CONF_USE_AUTH = "use_auth"

# Defaults
DEFAULT_PORT = 53595
DEFAULT_PASSWORD = "Projector"
DEFAULT_USE_AUTH = True
DEFAULT_NAME = "Sony Projector"

# Update intervals
SCAN_INTERVAL = 30  # seconds

# Input sources for VPL-XW5000
INPUT_SOURCES = {
    "hdmi1": "HDMI 1",
    "hdmi2": "HDMI 2",
}

# Picture modes for VPL-XW5000
PICTURE_MODES = {
    "cinema_film1": "Cinema Film 1",
    "cinema_film2": "Cinema Film 2",
    "reference": "Reference",
    "tv": "TV",
    "photo": "Photo",
    "game": "Game",
    "brt_cinema": "Bright Cinema",
    "brt_tv": "Bright TV",
    "user1": "User 1",
    "user2": "User 2",
    "user3": "User 3",
}

# Power states
POWER_STATE_MAP = {
    "standby": "off",
    "startup": "on",
    "on": "on",
    "cooling1": "off",
    "cooling2": "off",
}

# Display labels for the raw power_status reply
POWER_STATUS_LABELS = {
    "standby": "Off",
    "startup": "Warming up",
    "on": "On",
    "cooling1": "Cooling down",
    "cooling2": "Cooling down",
}

# Attribute name to ADCP read parameter, polled into extra_state_attributes
READ_SETTINGS = {
    "signal": "signal",
    "hdr_mode": "hdr",
    "color_temp": "color_temp",
    "color_space": "color_space",
    "gamma": "gamma_correction",
    "motionflow": "motionflow",
    "contrast_enhancer": "contrast_enh",
    "color": "color",
    "hue": "hue",
    "aspect": "aspect",
    "input_lag_reduction": "input_lag_red",
    "noise_reduction": "nr",
}

# Commands
CMD_POWER_ON = 'power "on"'
CMD_POWER_OFF = 'power "off"'
CMD_POWER_STATUS = "power_status ?"
CMD_INPUT = 'input "{}"'
CMD_INPUT_STATUS = "input ?"
CMD_BLANK_ON = 'blank "on"'
CMD_BLANK_OFF = 'blank "off"'
CMD_BLANK_STATUS = "blank ?"
CMD_PICTURE_MODE = 'picture_mode "{}"'
CMD_PICTURE_MODE_STATUS = "picture_mode ?"

# Adjustment commands (menu_num type)
CMD_BRIGHTNESS = "brightness {}"
CMD_BRIGHTNESS_STATUS = "brightness ?"
CMD_CONTRAST = "contrast {}"
CMD_CONTRAST_STATUS = "contrast ?"
CMD_SHARPNESS = "sharpness {}"
CMD_SHARPNESS_STATUS = "sharpness ?"
CMD_LIGHT_OUTPUT = "light_output_val {}"
CMD_LIGHT_OUTPUT_STATUS = "light_output_val ?"

# Reality Creation commands
CMD_REALITY_CREATION = 'real_cre "{}"'
CMD_REALITY_CREATION_STATUS = "real_cre ?"

# Remote key commands
CMD_KEY = 'key "{}"'
KEY_MENU = "menu"
KEY_RESET = "reset"
KEY_UP = "up"
KEY_DOWN = "down"
KEY_LEFT = "left"
KEY_RIGHT = "right"
KEY_ENTER = "enter"

# Responses
RESPONSE_OK = "ok"
ERROR_PREFIX = "err_"

# Display labels that the generic rule in label() would get wrong
LABEL_OVERRIDES = {
    "hdr10": "HDR10",
    "hlg": "HLG",
    "hdr_reference": "HDR Reference",
    "bt2020": "BT.2020",
    "bt709": "BT.709",
    "dci": "DCI",
    "adobe_rgb": "Adobe RGB",
    "true_cinema": "True Cinema",
    "v_stretch": "V Stretch",
    "brt_cinema": "Bright Cinema",
    "brt_tv": "Bright TV",
    "mid": "Mid",
}

# Parameters whose accepted values are a list, read with "<param> ? --range"
SELECT_PARAMS = (
    "picture_mode",
    "input",
    "color_temp",
    "color_space",
    "gamma_correction",
    "motionflow",
    "contrast_enh",
    "nr",
    "hdr",
    "aspect",
)
SWITCH_PARAMS = ("real_cre", "input_lag_red", "blank")

# Numeric parameters and the range used when the projector does not report one
NUMBER_DEFAULT_RANGES = {
    "brightness": {"min": 0, "max": 100},
    "contrast": {"min": 0, "max": 100},
    "sharpness": {"min": 0, "max": 100},
    "color": {"min": 0, "max": 100},
    "hue": {"min": 0, "max": 100},
    "light_output_val": {"min": 0, "max": 1000},
}


def label(value: Any) -> Any:
    """Turn a raw ADCP value into a display label, e.g. "gamma7" -> "Gamma 7"."""
    if value is None or not isinstance(value, str):
        return value
    if value in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[value]
    if re.fullmatch(r"-?\d+(\.\d+)?", value):
        return value
    text = value.replace("_", " ")
    if re.fullmatch(r"d\d+", text):
        return text.upper()
    match = re.fullmatch(r"(.*?)(\d+)", text)
    if match and match.group(1):
        return f"{match.group(1).rstrip().title()} {match.group(2)}"
    return text.title()


def option_label(param: str, value: Any) -> Any:
    """Display label for a raw value of a given ADCP parameter."""
    if param == "picture_mode" and value in PICTURE_MODES:
        return PICTURE_MODES[value]
    if param == "input" and value in INPUT_SOURCES:
        return INPUT_SOURCES[value]
    return label(value)
