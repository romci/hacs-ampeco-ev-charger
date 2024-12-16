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

## Sensors

The integration provides several sensors:
- Charger Status
- Charging Session
- Charging Current
- Charging Energy
- Charging Duration

## Services

Two main services are provided:
- `ev_charger.start_charging`: Start a charging session
- `ev_charger.stop_charging`: Stop the current charging session

## Installation

1. Copy the `custom_components/ev_charger` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Click the + button and search for "EV Charger"
5. Follow the configuration steps

## Configuration

You will need:
- ChargePoint ID
- Authentication Token
- API Host (optional, defaults to standard endpoint)

Unfortunately, AMPECO leaves it up to every vendor to implement their own login-flows, so sniffing out Authentication Token from your mobile app is currently both, the only possible way for a general-authentication flow, and hugely impractical.

## Development Status

This integration is under active development. Features and APIs may change without notice. Partially based off of AMPECO API documentation, particularly the "Driver App" sections: https://developers.ampeco.com/docs/overview

## Contributing

While this is primarily for personal use, suggestions and bug reports are welcome through the issue tracker.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not affiliated with any EV charger manufacturer or vendor. All product names, logos, and brands are property of their respective owners. 