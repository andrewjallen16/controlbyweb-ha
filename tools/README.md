# ControlByWeb – Home Assistant integration

Local-polling integration for ControlByWeb I/O modules. No cloud, no extra Python packages.

| Model | Protocol (auto-detected) | Entities |
|---|---|---|
| X-401, X-404, X-408, X-410, X-420 and other 400 series | `state.json` | see below |
| X-WR-1R12 and other older WebRelay units | `state.xml` | relay switch, pulse button, input, reboot state/count |

## Install
1. Copy `custom_components/controlbyweb` into your Home Assistant `config/custom_components/` folder.
2. Restart Home Assistant.
3. Settings → Devices & services → Add integration → **ControlByWeb**. Enter the IP address and login. Add the integration once per device.

## Entities (400 series)
| state.json key | Entity |
|---|---|
| `relayN` | Switch + "Relay N pulse" button |
| `digitalInputN`, `digitalION` (X-420) | Binary sensor |
| `oneWireSensorN` | Sensor (temperature/humidity; unit read from the device) |
| `analogInputN` (X-412/418/420), `frequencyInput` (X-420) | Sensor |
| `frequencyN`, `countN`, `onTimeN`, `totalOnTimeN` | Sensors (input functions) |
| `vin` / `vin1` | Sensor (volts) |
| `registerN`, `analogOutputN` | Number (writable) |

Entities for 1-Wire sensors and registers that the device reports as `x.x` (unused/unreadable) are skipped.

## Device-side requirements (from the manuals)
- **Every I/O needs a Local I/O number** under *I/O Setup*. I/O without a number is not in state.json, so it will not appear in Home Assistant. Reload the integration after changing I/O.
- Defaults: admin login `admin` / `webrelay`; the Control Page needs no password unless you enable one. Enabling it also disables Modbus/TCP (not used here). Change default passwords.
- Poll interval minimum is 3 s (the device's own `minRecRefresh`).

## Notes / limits
- **X-404 registers:** Modbus sensor readings appear as `registerN`. They are shown as writable Number entities because state.json does not say which registers are Modbus-mapped; avoid writing to those.
- **X-420 digital I/O** is shown read-only (direction is set on the device; the manuals don't document writing it over HTTP).
- **Older WebRelays (X-WR-1R12):** no serial number is reported, so the host:port is used as the unique ID. If a control password is enabled, any username works; the password is what matters. Automatic-Reboot-mode commands (reboot / disable) are not exposed.
- The "Model" dropdown only labels the device.

## Troubleshooting
    python3 tools/probe.py 192.168.1.2 --user admin --password webrelay
    python3 tools/probe.py 192.168.1.2 --password webrelay --path state.xml   # older WebRelay
    python3 tools/probe.py 192.168.1.2 --password webrelay --set showUnits=1  # read-only; shows 1-Wire units
On Windows, `tools\run_probe.bat` prompts for the details.
