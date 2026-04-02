# TomTuT Electrolux/AEG Dishwasher

Home Assistant custom integration + Lovelace card for AEG/Electrolux dishwashers via the Electrolux OCP Cloud API.

## Features

### Integration
- Real-time dishwasher status (Running, Paused, Idle, Finished, etc.)
- Cycle phase tracking (Prewash, Main Wash, Rinse, Drying, Door Drying)
- Remaining time + estimated finish time
- Program selection (ECO, AUTO, Quick, etc.)
- Door state, WiFi quality, connection status
- Salt and rinse aid warnings
- Alexa-ready spoken status sensor (German)
- Remote control: Start, Pause, Resume, Stop/Reset, On, Off

### Lovelace Card
- Status-dependent dishwasher images (closed, running, finished)
- Animated blue glow overlay when running
- Timer with finish time on the image
- Control buttons (context-dependent per state)
- Warning badges for salt/rinse aid
- Optional power consumption display (e.g. via Shelly Plug)
- Dark theme, responsive

## Installation

### HACS (Recommended)
1. Open HACS in Home Assistant
2. Click the three dots menu > Custom repositories
3. Add `https://github.com/TomTuT1242/tomtut-electrolux-dishwasher` as **Integration**
4. Install "TomTuT Electrolux/AEG Dishwasher"
5. Restart Home Assistant

### Manual
1. Copy `custom_components/electrolux_dishwasher/` to your HA `config/custom_components/`
2. Copy `card/tomtut-dishwasher-card.js` to `config/www/`
3. Copy `card/images/` to `config/www/tomtut-dishwasher/`
4. Add `/local/tomtut-dishwasher-card.js` as a Lovelace resource (JavaScript Module)
5. Restart Home Assistant

## Configuration

### Integration Setup
1. Go to Settings > Devices & Services > Add Integration
2. Search for "Electrolux"
3. Enter your AEG/Electrolux account email
4. Enter the OTP code received by email
5. Your dishwasher is automatically discovered

### Lovelace Card

```yaml
type: custom:tomtut-dishwasher-card
entity_state: sensor.geschirrspulmaschine_status
entity_phase: sensor.geschirrspulmaschine_phase
entity_program: sensor.geschirrspulmaschine_programm
entity_time: sensor.geschirrspulmaschine_restzeit
entity_door: binary_sensor.geschirrspulmaschine_tur
entity_running: binary_sensor.geschirrspulmaschine_lauft
entity_salt: binary_sensor.geschirrspulmaschine_salz_fehlt
entity_rinse_aid: binary_sensor.geschirrspulmaschine_klarspuler_niedrig
# Optional: power consumption sensor (e.g. Shelly Plug)
entity_power: sensor.shelly_plug_dishwasher_power
# Buttons
button_on: button.geschirrspulmaschine_einschalten
button_off: button.geschirrspulmaschine_ausschalten
button_start: button.geschirrspulmaschine_start
button_pause: button.geschirrspulmaschine_pause
button_resume: button.geschirrspulmaschine_fortsetzen
button_stopreset: button.geschirrspulmaschine_stop_reset
```

## Entities Created

### Sensors
| Entity | Description |
|--------|-------------|
| `sensor.*_status` | Appliance state (RUNNING, IDLE, etc.) |
| `sensor.*_phase` | Current cycle phase |
| `sensor.*_programm` | Selected program |
| `sensor.*_restzeit` | Time remaining (minutes) |
| `sensor.*_fertig_um` | Estimated finish timestamp |
| `sensor.*_sprachstatus` | Spoken status for voice assistants |
| `sensor.*_warnungen` | Alert count with details |
| `sensor.*_wlan` | WiFi signal quality |

### Binary Sensors
| Entity | Description |
|--------|-------------|
| `binary_sensor.*_lauft` | Running state |
| `binary_sensor.*_tur` | Door open/closed |
| `binary_sensor.*_verbunden` | Cloud connection |
| `binary_sensor.*_salz_fehlt` | Salt missing warning |
| `binary_sensor.*_klarspuler_niedrig` | Rinse aid low warning |

### Buttons
| Entity | Description |
|--------|-------------|
| `button.*_einschalten` | Power on |
| `button.*_ausschalten` | Power off |
| `button.*_start` | Start program |
| `button.*_pause` | Pause program |
| `button.*_fortsetzen` | Resume program |
| `button.*_stop_reset` | Stop/Reset |

## Remote Start

To start the dishwasher remotely, you must first enable Remote Start on the appliance:
1. Press and hold the **Delay** button for 3 seconds
2. The lock icon will illuminate
3. Close the door

Remote Start must be re-enabled before each remote start cycle.

## Notes

- This integration uses the Electrolux OCP Cloud API (same API as the official AEG app)
- Authentication is via email OTP (no password needed)
- Polling interval: 30 seconds
- The API keys used are the same public keys from the AEG mobile app, also used by other open-source projects

## License

MIT License - see [LICENSE](LICENSE)
