# ControlByWeb 400 Series – Home Assistant integration

Local-polling integration for ControlByWeb X-400 series modules (X-401, X-410, X-412, X-417, X-418, X-420, X-404, X-400 + expansion, and W/C variants). It uses the device's built-in HTTP interface (`/state.json`); no cloud and no extra Python dependencies.

## Install
1. Copy `custom_components/controlbyweb` into your HA config's `custom_components/` folder (or add this repo to HACS as a custom repository).
2. Restart Home Assistant.
3. Settings → Devices & services → Add integration → **ControlByWeb 400 Series**.

## Entities
| state.json key | Entity |
|---|---|
| `relayN` | Switch, plus a "Relay N pulse" button |
| `digitalInputN` | Binary sensor |
| `oneWireSensorN`, `analogInputN` | Sensor (unit = whatever the device is set to report) |
| `vin` | Sensor (volts) |
| `registerN`, `analogOutputN` | Number (writable) |

## Device-side requirements (from the manual)
- **Every I/O needs a "Local Relay/Input/Sensor/… Number" assigned** under *I/O Setup*. Unassigned I/O does **not** appear in state.json, so it will not appear in Home Assistant.
- Default Control Page access has no password. If you enable one, enter the `user` (or `admin`) credentials in the integration. Enabling the Control Page password also disables Modbus/TCP, which is one reason this integration uses HTTP.
- After adding or renumbering I/O on the device, reload the integration.
- Default admin login is `admin` / `webrelay`. Change it.

## Verify before you rely on it
The supplied manual does not document the state.json schema or command syntax, so these were implemented from the manual's MQTT section (which says control messages use the same `relay2=1&register1=5.5` parameters as HTTP GET) and from general knowledge of the product. Run the probe against your device first:

    python3 tools/probe.py 192.168.1.2 [--user admin --password ...]

Check that the keys match the table above. If a key name differs, edit the `PREFIX_*` constants in `const.py`. Also confirm the relay commands: `relayN=0` off, `1` on, `2` pulse (`RELAY_*` in `const.py`).
