# Home Assistant AMPECO EV Charger Integration

A Home Assistant custom integration for AMPECO EV Charger control and monitoring. This integration is currently for personal use and is not production ready. Actually, I'm not even sure it will work outside of the white-labeled vendor of my particular charger (MegaTel).

**Author**: Roman Avsec
**License**: GPL-3.0

## ⚠️ Disclaimer

This integration is currently in development and intended for personal use. It is not production ready and may contain bugs or incomplete features. Use at your own risk.

## Features

- Real-time charger status monitoring
- Charging session control (start/stop)
- Power and energy consumption tracking
- Smart charging capabilities
- Detailed charging session information
- Adaptive polling intervals (30s during charging, 5min idle)

## Sensors

The integration provides several sensors for each charger. Each sensor has a unique entity ID prefixed with `sensor.evse_` followed by the chargepoint ID in lowercase slug format (e.g., `sensor.evse_abcxyz_charging_current`). This ensures that when multiple chargers are added, their entity IDs won't conflict.

Available sensors include:
- **Status**: Current status of the charger (`sensor.evse_abcxyz_charger_status`)
- **Charging Session**: Active charging session information with power in kW (`sensor.evse_abcxyz_charging_session`)
- **Charging Current**: Current charging rate in amperes (`sensor.evse_abcxyz_charging_current`)
- **Charging Energy**: Total energy delivered in kWh (`sensor.evse_abcxyz_charging_energy`)
- **Charging Duration**: Duration of the active charging session in minutes (`sensor.evse_abcxyz_charging_duration`)
- **EVSE Status**: Status of the specific EVSE (connector) (`sensor.evse_abcxyz_evse_status`)
- **Polling Interval** (diagnostic): Current update interval with charging state info (`sensor.evse_abcxyz_polling_interval`)
- **Maximum Current** (diagnostic): Maximum allowed charging current (`sensor.evse_abcxyz_max_current`)
- **Last Month Energy** (diagnostic): Energy used in the previous month (`sensor.evse_abcxyz_last_month_energy`)
- **Session ID** (diagnostic): Active charging session identifier (`sensor.evse_abcxyz_session_id`)

Each sensor will display with a friendly name combining the charger name and sensor type (e.g., "My House Charging Current").

## Unit Conversions

The integration handles several unit conversions to ensure values are displayed correctly:

- **Power**: Values are converted from watts (W) to kilowatts (kW) when needed
- **Energy**: Values are converted from watt-hours (Wh) to kilowatt-hours (kWh) when needed
- **Duration**: Values are converted from seconds to minutes for easier reading

These conversions ensure that the values displayed in Home Assistant match what you see in the official AMPECO app.

## Services

The integration provides services to control your chargers:

- `ampeco_ev_charger.start_charging`: Start a charging session for a specific device
  - Required parameter: `device_id` - The ID of the EV charger device to start
  - Optional parameter: `max_current` - Maximum charging current in amperes (6-32A)

- `ampeco_ev_charger.stop_charging`: Stop the current charging session for a specific device
  - Required parameter: `device_id` - The ID of the EV charger device to stop

- `ampeco_ev_charger.update_data`: Manually trigger a data update for a specific device
  - Required parameter: `device_id` - The ID of the EV charger device to update

When multiple chargers are configured, you must specify the `device_id` to target the correct charger. The device ID is different from the entity ID and remains consistent even after our recent entity ID changes.

### Finding the Device ID for Service Calls

To find the correct device ID for service calls:

1. Go to **Settings** > **Devices & Services** in your Home Assistant dashboard
2. Find your AMPECO EV Charger in the list and click on it
3. In the URL bar, you'll see a path like `/config/devices/device/abc123...` - the last part after `/device/` is your device ID
4. Alternatively, use the Developer Tools > Services panel, where you can select your device from a dropdown when calling the service

Note that device IDs are long strings (like `c9d46d418ffe1819e551c5d8c8e7f05e`) and are different from the entity IDs (like `sensor.evse_qng0c18010_charging_current`). Always use the device ID for service calls.

## Installation

### HACS Installation (Recommended)
1. Add this repository to HACS as a custom repository
   - Repository: `romci/hacs-ampeco-ev-charger`
   - Category: `Integration`
2. Install the integration through HACS
3. Restart Home Assistant
4. Add the integration through the HA interface

### Manual Installation
1. Copy the `custom_components/ampeco_ev_charger` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Click the + button and search for "AMPECO EV Charger"
5. Follow the configuration steps

## Configuration

You will need:
- Your ChargePoint ID
- Authentication Token
- API Host (optional, defaults to standard endpoint)

Unfortunately, AMPECO leaves it up to every vendor to implement their own login-flows, so sniffing out Authentication Token from your mobile app is currently both, the only possible way for a general-authentication flow, and hugely impractical.

### Finding Your Authentication Token
1. Use your browser's developer tools or a mobile proxy like Charles
2. Monitor network traffic while using your charger's mobile app
3. Look for API requests to the AMPECO backend
4. Extract the Bearer token from the Authorization header

## Advanced Features

### Adaptive Polling
The integration implements an adaptive polling strategy:
- 30-second intervals during active charging
- 5-minute intervals when idle
- Automatic adjustment based on charging state
- Exponential backoff on errors

### Diagnostic Information
The integration provides diagnostic information through:
- Polling interval sensor with charging state
- Detailed error logging
- Retry count and timing information

## Development Status

This integration is under active development. Features and APIs may change without notice. Partially based off of AMPECO API documentation, particularly the "Driver App" sections: https://developers.ampeco.com/docs/overview

## Contributing

While this is primarily for personal use, suggestions and bug reports are welcome through the issue tracker.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not affiliated with, endorsed by, or connected to AMPECO or any EV charger manufacturer or vendor. All product names, logos, and brands are property of their respective owners.
