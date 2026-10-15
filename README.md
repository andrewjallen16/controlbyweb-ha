# ControlByWeb 400 series - Home Assistant integration

Local-polling integration for ControlByWeb 400 series I/O modules (`state.json`). No cloud, no extra Python packages.
Needs Home Assistant 2025.1 or newer (2026.3+ to show the bundled logo).

> Before publishing, replace `your-user` in `manifest.json` (documentation and issue tracker URLs) and add yourself to `codeowners`.

## Supported modules
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

**Linked I/O:** a module can mirror I/O from other modules (P2P / expansion). It appears in `state.json` like local I/O, so a gateway such as the X-404 can show relays and inputs that physically live on other devices. Controlling a linked relay through the gateway should work the same way, but this has not been tested.

Not supported: older WebRelay units (e.g. X-WR-1R12) - they have no `state.json`.

## Install
1. Copy `custom_components/controlbyweb` into your Home Assistant `config/custom_components/` folder.
2. Restart Home Assistant.
3. Settings -> Devices & services. Modules whose MAC starts `00:0C:C8` are **discovered automatically**; otherwise use Add integration -> **ControlByWeb** and enter the IP address and login.
4. Confirm the model. It is shown on the device page and in the device name.

Add the integration once per module. If DHCP gives a module a new IP address, discovery notices and updates it automatically (a fixed IP is still recommended).

## Entities
| state.json key | Entity |
|---|---|
| `relayN` | Switch + "Relay N pulse" button |
| `digitalInputN`, `digitalION` (X-420) | Binary sensor |
| `oneWireSensorN` | Sensor (temperature/humidity; unit read from the device) |
| `analogInputN`, `frequencyInput` (X-420) | Sensor |
| `frequencyN`, `countN`, `onTimeN`, `totalOnTimeN` | Sensors, plus "reset" buttons for count / on time / total on time |
| `vin` / `vin1` | Sensor (volts) |
| `registerN` | Sensor (read-only by default), or Number if writing is enabled |
| `analogOutputN` | Number (writable) |

- Sensors the device reports as `x.x` (unplugged probe, unused register) are shown as **unavailable**, or skipped if they were never configured. If one is connected or configured later it **appears without reloading** the integration.
- Entity names are translatable ("Relay 1").

## Options (Configure button)
| Option | Default | What it does |
|---|---|---|
| Model | as chosen | Shown on the device. |
| Polling interval | 5 s (min 3) | The device's own minimum is 3 s. |
| Fallback 1-Wire unit | none | Only used if the device doesn't report a unit. |
| Use I/O names from the device | off | Names entities after the names set on the module (see below). |
| Allow writing registers | off | Registers become editable Number boxes instead of read-only sensors. |

### Device names (experimental)
The module offers `customState.json`, the same data keyed by your own I/O names in camelCase. The manual doesn't say how its entries line up with `state.json`, so the integration pairs them **by position** and only uses the names if both files have the same number of entries and their values agree. Names are rebuilt from camelCase ("gasTank" -> "Gas Tank"), so spacing and capitals may differ from what you typed. Check your own unit first:

    python3 tools/probe.py 192.168.1.2 --password webrelay --names

If every row pairs the right I/O, turn the option on. Names are read when the integration loads; reload it after renaming I/O on the device.

## Services
**`controlbyweb.pulse`** - pulse a relay switch for a chosen time (0.1 to 86400 seconds). It applies to that one pulse and does not change the pulse time saved on the device.

    action: controlbyweb.pulse
    target:
      entity_id: switch.my_relay
    data:
      duration: 2.5

## Diagnostics
Device page -> three-dot menu -> **Download diagnostics**. Passwords, usernames, host, serial number and location are redacted. It includes the raw `state.json`, `customState.json`, and the integration's model guess.

## Device-side requirements (from the manuals)
- **Every I/O needs a Local I/O number** under *I/O Setup*; otherwise it is not in state.json and won't appear in Home Assistant.
- Defaults: admin login `admin` / `webrelay`; the Control Page needs no password unless you enable one (which also disables Modbus/TCP, not used here). Change default passwords.

## Notes and limits
- **X-404 registers:** Modbus readings appear as `registerN`. That's why registers are read-only by default; enabling writes on an X-404 can write to the Modbus device behind a register.
- **X-417 analog outputs:** the manuals don't give the `state.json` key; `analogOutputN` is assumed and unverified. Values are in the engineering units set on the device and the Number entity does not limit the range, so check your output scaling before writing to a valve or actuator.
- **X-420 digital I/O** is shown read-only (direction is set on the device; the manuals don't document writing it over HTTP).

## Security
- Login uses HTTP Basic. Over plain HTTP the password is visible on the network; that is normally acceptable on a trusted LAN. Use HTTPS if your module supports it and the network isn't trusted.
- Modules ship with self-signed certificates, so HTTPS certificate checking is **off** unless you tick "Verify HTTPS certificate" when adding the device.
- The password is hidden in the setup form and redacted from diagnostics.

## Branding
`custom_components/controlbyweb/brand/` holds `icon`, `logo`, `dark_icon`, `dark_logo` (+ `@2x`). The supplied logo is white-only, so the light-theme `logo.png` is a dark-slate recolour and the icon is the white "CBW" letters on a slate tile. Replace the PNGs with official colour artwork if you have it. Home Assistant caches brand images; hard-refresh the browser if an old image shows.

## Development
    pip install -r requirements_test.txt
    pytest

`tests/test_const.py` is pure logic. The other tests use `pytest-homeassistant-custom-component` (config flow, DHCP, setup, services, dynamic entities, diagnostics). GitHub Actions run hassfest, HACS validation and pytest (`.github/workflows`).

## Troubleshooting
    python3 tools/probe.py 192.168.1.2 --user admin --password webrelay
    python3 tools/probe.py 192.168.1.2 --password webrelay --set showUnits=1   # read-only; shows 1-Wire units
    python3 tools/probe.py 192.168.1.2 --password webrelay --names             # custom-name alignment
On Windows, `tools\run_probe.bat` prompts for the details.
