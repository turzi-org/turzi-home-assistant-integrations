"""Constants for the Akuvox integration."""

DOMAIN = "akuvox"

# Config entry keys
CONF_MODEL = "model"
CONF_MAC_ADDRESS = "mac_address"
CONF_DEVICE_IP = "device_ip"
CONF_API_USERNAME = "api_username"
CONF_API_PASSWORD = "api_password"
CONF_RELAYS = "relays"
CONF_INPUTS = "inputs"

# Per-relay config keys
CONF_RELAY_NAME = "name"
CONF_RELAY_DEVICE_CLASS = "device_class"
CONF_RELAY_IS_LOCK = "is_lock"
CONF_RELAY_LOCK_DELAY = "lock_delay"
CONF_RELAY_LOCK_LEVEL = "lock_level"

# Per-input config keys
CONF_INPUT_NAME = "name"
CONF_INPUT_DEVICE_CLASS = "device_class"

# Webhook
WEBHOOK_ID_PREFIX = "akuvox_"

# Platforms
PLATFORMS = ["switch", "binary_sensor", "lock", "event"]

# Relay letters for naming
RELAY_LETTERS = ["A", "B", "C", "D"]

# Default lock delay (seconds)
DEFAULT_LOCK_DELAY = 3

# Default relay level (0=NC-COM, 1=NO-COM)
DEFAULT_RELAY_LEVEL = 0

# Supported binary sensor device classes for inputs
INPUT_DEVICE_CLASSES = [
    "door",
    "window",
    "motion",
    "garage_door",
    "opening",
    "safety",
    "tamper",
]

# Supported switch device classes for relays
RELAY_DEVICE_CLASSES = [
    "switch",
    "outlet",
]

# Model registry — all supported Akuvox models and their capabilities
# Each model defines:
#   name: Display name
#   relays: Number of relay outputs
#   inputs: Number of dry-contact inputs
#   tamper: Whether the device has a tamper alarm
#   events: List of supported access event types
MODEL_REGISTRY: dict[str, dict] = {
    "S539": {
        "name": "Akuvox S539",
        "relays": 3,
        "inputs": 3,
        "tamper": False,
        "events": ["face", "qr", "card", "code", "breakin"],
    },
    "S535": {
        "name": "Akuvox S535",
        "relays": 1,
        "inputs": 2,
        "tamper": False,
        "events": ["face", "qr", "card", "code", "breakin"],
    },
    "S532": {
        "name": "Akuvox S532",
        "relays": 2,
        "inputs": 4,
        "tamper": False,
        "events": ["card", "code"],
    },
    "X916": {
        "name": "Akuvox X916",
        "relays": 4,
        "inputs": 4,
        "tamper": False,
        "events": ["face", "card", "code", "breakin"],
    },
    "X915V2": {
        "name": "Akuvox X915V2",
        "relays": 3,
        "inputs": 3,
        "tamper": False,
        "events": ["face", "qr", "card", "code", "breakin"],
    },
    "X912": {
        "name": "Akuvox X912",
        "relays": 2,
        "inputs": 3,
        "tamper": False,
        "events": ["face", "card", "code", "breakin"],
    },
    "X910": {
        "name": "Akuvox X910",
        "relays": 2,
        "inputs": 2,
        "tamper": False,
        "events": ["card", "breakin"],
    },
    "R29": {
        "name": "Akuvox R29",
        "relays": 3,
        "inputs": 3,
        "tamper": False,
        "events": ["face", "qr", "card", "code", "breakin"],
    },
    "R28V2": {
        "name": "Akuvox R28V2",
        "relays": 3,
        "inputs": 3,
        "tamper": False,
        "events": ["card", "code"],
    },
    "R20_Series": {
        "name": "Akuvox R20 Series",
        "relays": 2,
        "inputs": 2,
        "tamper": False,
        "events": ["card", "code"],
    },
    "R25_Series": {
        "name": "Akuvox R25 Series",
        "relays": 2,
        "inputs": 2,
        "tamper": False,
        "events": ["card", "code"],
    },
    "E18": {
        "name": "Akuvox E18",
        "relays": 2,
        "inputs": 3,
        "tamper": True,
        "events": ["face", "card", "code"],
    },
    "E16V2": {
        "name": "Akuvox E16V2",
        "relays": 1,
        "inputs": 1,
        "tamper": True,
        "events": ["face", "card", "code"],
    },
    "E13": {
        "name": "Akuvox E13",
        "relays": 1,
        "inputs": 2,
        "tamper": False,
        "events": ["card", "motion"],
    },
    "E12": {
        "name": "Akuvox E12",
        "relays": 1,
        "inputs": 2,
        "tamper": False,
        "events": ["card", "motion"],
    },
    "A094": {
        "name": "Akuvox A094",
        "relays": 4,
        "inputs": 0,
        "tamper": True,
        "events": ["card", "code"],
    },
    "A05": {
        "name": "Akuvox A05",
        "relays": 1,
        "inputs": 1,
        "tamper": True,
        "events": ["face", "card"],
    },
    "A03": {
        "name": "Akuvox A03",
        "relays": 1,
        "inputs": 2,
        "tamper": True,
        "events": ["card"],
    },
    "A02": {
        "name": "Akuvox A02",
        "relays": 1,
        "inputs": 2,
        "tamper": True,
        "events": ["card", "code"],
    },
    "A01": {
        "name": "Akuvox A01",
        "relays": 1,
        "inputs": 2,
        "tamper": True,
        "events": ["card"],
    },
}
