"""Constants for the Electrolux/AEG Dishwasher integration."""

DOMAIN = "electrolux_dishwasher"

# OCP API
OCP_BASE_URL = "https://api.ocp.electrolux.one"
OCP_WS_URL = "wss://ws.ocp.electrolux.one"
OCP_API_KEY = "PEdfAP7N7sUc95GJPePDU54e2Pybbt6DZtdww7dz"
OCP_CLIENT_ID = "AEGOneApp"
OCP_CLIENT_SECRET = (
    "G6PZWyneWAZH6kZePRjZAdBbyyIu3qUgDGUDkat7obfU9ByQSgJPNy8xRo99vzcg"
    "WExX9N48gMJo3GWaHbMJsohIYOQ54zH2Hid332UnRZdvWOCWvWNnMNLalHoyH7xU"
)

# Gigya
GIGYA_API_KEY = "4_A4U-T1cdVL3JjsFffdPnUg"
GIGYA_DOMAIN = "eu1.gigya.com"

# Refresh interval for polling (seconds)
SCAN_INTERVAL = 30

# Appliance states
APPLIANCE_STATES = [
    "OFF", "IDLE", "READY_TO_START", "RUNNING",
    "PAUSED", "DELAYED_START", "END_OF_CYCLE", "ALARM",
]

CYCLE_PHASES = [
    "PREWASH", "MAINWASH", "HOTRINSE", "COLDRINSE",
    "EXTRARINSE", "DRYING", "ADO_DRYING", "UNAVAILABLE",
]

PROGRAMS = [
    "AUTO", "QUICK_30", "INTENSIVE_70", "ECO",
    "GLASS_CARE", "NIGHT_60", "RINSE_AND_HOLD",
]

COMMANDS = ["ON", "OFF", "START", "PAUSE", "RESUME", "STOPRESET"]
