# ControlByWeb 400 series – Home Assistant integration

Local-polling integration for ControlByWeb 400 series I/O modules (`state.json`). No cloud, no extra Python packages.
Requires Home Assistant 2026.3 or newer to show the bundled logo (it works on older versions without it).

| Model | What it is | Entities you can expect |
|---|---|---|
| X-400 / X-400C (cellular) | Expandable master; up to 32 expansion or P2P modules | Whatever I/O has a Local number, local or linked |
| X-401 | 2 digital inputs, 2 relays | 2 switches (+ pulse), 2 binary sensors |
| X-404 | RS-485 Modbus gateway | Modbus data as registers, plus any linked I/O and 1-Wire |
| X-405 / X-406 | 1-Wire sensor interfaces | 1-Wire temperature/humidity sensors |
| X-408 | 8 digital inputs | 8 binary sensors (+ counter / frequency / timer sensors if configured) |
| X-410 | 4 relays, 4 digital inputs, up to 16 temp sensors | 4 switches (+ pulse), 4 binary sensors, 1-Wire sensors |
| X-412 | 4 relays, 4 analog inputs | switches, analog sensors |
| X-417 | 1-5 analog outputs | writable Number entities (see notes) |
| X-418 | 8 analog inputs | 8 analog sensors |
| X-420 | analog + digital I/O, frequency input | analog/frequency sensors, digital I/O, counters, 1-Wire |

**Linked I/O:** a module can mirror I/O from other modules (P2P / expansion). It appears in `state.json` like local I/O, so a gateway such as the X-404 can show relays and inputs that physically live on other devices. Controlling a linked relay through the gateway should work the same way, but I have not tested it.

Not supported: older WebRelay units (e.g. X-WR-1R12) - they have no `state.json`.

## Install
1. Copy `custom_components/controlbyweb` into your Home Assistant `config/custom_components/` folder. If Home Assistant is run as a Docker, copy `custom_components/controlbyweb` to the /data folder.
2. Restart Home Assistant.
3. Settings -> Devices & services -> Add integration -> **ControlByWeb**. Enter the IP address and login, then confirm the model. Add the integration once per device.

The **model** you confirm is shown on the device page in Home Assistant (and in its name). The module can't report its own model, and linked I/O makes counting relays and inputs unreliable, so the integration only makes a guess (for example, 2 relays + 2 inputs defaults to X-401) and asks you to confirm. Change it any time under the integration's **Configure** button.

## Entities
| state.json key | Entity |
|---|---|
| `relayN` | Switch + "Relay N pulse" button |
| `digitalInputN`, `digitalION` (X-420) | Binary sensor |
| `oneWireSensorN` | Sensor (temperature/humidity; unit read from the device) |
| `analogInputN`, `frequencyInput` (X-420) | Sensor |
| `frequencyN`, `countN`, `onTimeN`, `totalOnTimeN` | Sensors (input functions) |
| `vin` / `vin1` | Sensor (volts) |
| `registerN`, `analogOutputN` | Number (writable) |

1-Wire sensors and registers the device reports as `x.x` (unused/unreadable) are skipped.

## Device-side requirements (from the manuals)
- **Every I/O needs a Local I/O number** under *I/O Setup*; otherwise it is not in state.json and won't appear in Home Assistant. Reload the integration after changing I/O.
- Defaults: admin login `admin` / `webrelay`; the Control Page needs no password unless you enable one (which also disables Modbus/TCP, not used here). Change default passwords.
- Poll interval minimum is 3 s (the device's own `minRecRefresh`).

## Notes / limits
- **X-404 registers:** Modbus sensor readings appear as `registerN`. They are shown as writable Number entities because state.json doesn't say which registers are Modbus-mapped; avoid writing to those.
- **X-417 analog outputs:** the manuals don't give the `state.json` key; `analogOutputN` is assumed and unverified. Values are in the engineering units you configured on the device, and the Number entity does not limit the range, so check your output scaling before writing to a valve or actuator.
- **X-420 digital I/O** is shown read-only (direction is set on the device; the manuals don't document writing it over HTTP).

## Branding
`custom_components/controlbyweb/brand/` holds `icon`, `logo`, `dark_icon`, `dark_logo` (+ `@2x`). The supplied logo is white-only, so the light-theme `logo.png` is a dark-slate recolour and the icon is the white "CBW" letters on a slate tile. Replace any of these PNGs with official colour artwork if you have it. Home Assistant caches brand images; hard-refresh the browser if the old image shows.

## Troubleshooting
    python3 tools/probe.py 192.168.1.2 --user admin --password webrelay
    python3 tools/probe.py 192.168.1.2 --password webrelay --set showUnits=1   # read-only; shows 1-Wire units
On Windows, `tools\run_probe.bat` prompts for the details.
