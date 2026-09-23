"""Constants for Sony Projector ADCP integration."""

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