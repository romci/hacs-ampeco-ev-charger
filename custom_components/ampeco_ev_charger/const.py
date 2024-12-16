"""Constants for the AMPECO EV Charger integration."""

from datetime import timedelta

DOMAIN = "ampeco_ev_charger"
SCAN_INTERVAL = timedelta(seconds=30)

# API
DEFAULT_API_HOST = "https://app.ampeco.global"  # Updated to actual AMPECO API host
CONF_API_HOST = "api_host"

# Config flow constants
CONF_CHARGEPOINT_ID = "chargepoint_id"
CONF_AUTH_TOKEN = "auth_token"
CONF_EVSE_ID = "evse_id"

# Sensor types
SENSOR_TYPE_CHARGER_STATUS = "charger_status"
SENSOR_TYPE_CHARGING_SESSION = "charging_session"

# Service names
SERVICE_START_CHARGING = "start_charging"
SERVICE_STOP_CHARGING = "stop_charging"

# Error messages
ERROR_AUTH_INVALID = "invalid_auth"
ERROR_CANNOT_CONNECT = "cannot_connect"

# Add these constants
DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3
MIN_TIME_BETWEEN_RETRIES = timedelta(minutes=1)
