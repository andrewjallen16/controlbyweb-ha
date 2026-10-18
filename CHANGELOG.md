# Changelog

Versions follow `custom_components/controlbyweb/manifest.json`. Download files are named
`ha-controlbyweb-v<version>.zip` (everything) and `ha-controlbyweb-v<version>-patch.zip`
(only the files changed since the previous patch, so your README and manifest are not overwritten).

## 0.9.2
- Each timer now has a "Timer N set" number box: type the seconds to start the timer (it shows the time
  left while it runs; 0 stops it). The `controlbyweb.start_timer` service and the cancel button remain.

## 0.9.1
- Modules powered over Ethernet (PoE) read 0 V on the Vin terminals, so "Supply voltage 0 V" is no longer
  created for them; an existing one is removed once. It comes back by itself if a DC supply is connected.
- New diagnostic "Power source" sensor (PoE or DC input) on modules where it applies: "-E" models
  (PoE and/or DC; the model number comes from diagnostics.xml) and any module that reads 0 V on Vin.

## 0.9.0
- Device card now shows the module's real model number (for example "X-404-I") and firmware version,
  read from `diagnostics.xml` (no password needed; skipped quietly on firmware without it).
- New diagnostic "Uptime" sensor, from `deviceUptime` in state.json (updates once a minute).
- Setup pre-selects the model the module reports instead of guessing; the downloadable diagnostics
  include the module's diagnostics.xml.

## 0.8.0
- Timers can now be controlled: new `controlbyweb.start_timer` service (seconds; 0 stops) and a
  "Timer N cancel" button. Starting a timer with `state.json?timer1=30` was confirmed on an X-420;
  stopping with `timer1=0` is assumed to work the same way.

## 0.7.2
- Fix: sensors without a unit of their own (unit-less registers, analog inputs, counters) were never
  registered in Home Assistant.
- Sensors now get a device class from the unit the module reports (A, V, W, VA, var, Hz, kWh, Wh, temperature).
  Energy sensors use `total_increasing`. "Deg" becomes the degree sign.

## 0.7.1
- Fix: HTTP Basic login is built by hand (aiohttp.BasicAuth is deprecated).
- Tests: fake-device URL now matches real requests; device-name test data ordered correctly;
  failing check lists everything that was registered.

## 0.7.0
- Read-only timer sensors (`timerN`), confirmed on an X-420.
- Keys the integration doesn't use are logged once and listed in the diagnostics download.

## 0.6.0
- X-420 frequency input (`frequencyInput1`) with a unit option (mph, km/h, m/s, knots, Hz); wind-speed device class.
- An I/O that has been seen keeps its entity (unavailable while unplugged).
- One-time cleanup of empty 1-Wire / register entities left by older versions.
- `x.x` followed by a unit is treated as unreadable.

## 0.5.0
- Optional device I/O names (opt-in), read-only registers by default, entities added without reload,
  diagnostics download, DHCP discovery (00:0C:C8), `controlbyweb.pulse` service, counter/timer reset buttons,
  masked password and HTTPS certificate option, tests and GitHub workflows.

## 0.4.x
- Full 400 series model list (X-400 to X-420) with a model guess; 0.4.1 fixed a broken import.

## 0.3.0
- 400 series only; model confirmation step; bundled logo and icons.

## 0.2.0
- Auto-detect protocol, 1-Wire units from the module, X-420 and X-410 I/O.

## 0.1.0
- First version: relays, digital inputs, 1-Wire sensors, registers over `state.json`.
