# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A DIY **19" 2U rack-mount smart temperature-controlled fan** — not a software app, but three tightly-coupled deliverables for one physical build, plus design docs:

- **`cad/`** — parametric 3D-printed front panel + mounts (build123d → STEP/STL for a Bambu P1S).
- **`firmware/`** — Arduino UNO R4 WiFi firmware (single `.ino`).
- **`homeassistant/`** + firmware MQTT discovery — Home Assistant / HomeKit integration.

This is an open-source project: code comments and UI strings are in **English**. Docs are bilingual — `README.md` / `cad/README.md` (English, primary) each have a Simplified Chinese twin `README.zh-CN.md` / `cad/README.zh-CN.md`; any doc change must be applied to both languages.

## The cross-subsystem couplings (read this first)

The hardware, firmware, wiring diagram, and docs encode the **same physical facts in several places** — changing one almost always requires changing the others:

- **Pinout** (fan PWM=D9 split to all 3 fans via a **PST daisy-chain**, TACH=D2 `INPUT_PULLUP` from the **master fan only** — PST shares PWM/12V/GND so the downstream fans have no individual tach; DS18B20=D4, KY-040 CLK=D3/DT=D6/SW=D12 — CLK is on **D3** because the R4 only does external interrupts on D2/D3 and D2 is the TACH; D5 silently won't interrupt, OLED=I²C SDA/SCL) lives in `firmware/smartfan/smartfan.ino`, `README.md` + `README.zh-CN.md` (§2 Schematic / §3 Wiring), and `tools/gen_breadboard.py` + `tools/gen_schematic.py`. Change all together.
- **Direct wiring**: all modules connect **directly to the Arduino** via **two 1-to-3 dupont splitter cables** (one off the 5V pin, one off a GND pin, each fanning out to OLED/DS18B20/KY-040); the fan 4P (PST master) and all signal lines plug straight into the headers (fan GND takes a second GND pin, +12V→VIN). This fact lives in both READMEs (BOM, §3 Wiring, §5 Assembly), `tools/gen_breadboard.py` (→ `tools/wiring.png`) + `tools/gen_schematic.py`, and the CAD. Change together.
- **Arduino mounting orientation ↔ display choice**: the board is mounted **flipped** (`Rot(180,0,0)` in `gen_step`, `ARD_HOLES` configured to match) so its component side / pin headers face **backward (+Y)** — that's what gives dupont wires room (the original headers-toward-panel layout had no clearance). Consequences encoded across files: the onboard 12×8 matrix now faces inward and is unused, so the **front display is a 0.96" I²C OLED** (`OLED_*` params + an OLED pocket in the CAD; `Adafruit_SSD1306` in firmware). The USB-C/DC edge still faces +X so the 12V plug clears fan 1 (the master fan, nearest the control area). If you change the mount orientation, `ARD_HOLES` + `ARD_STANDOFF_H` + the OLED-vs-matrix display path move together. The KY-040 mounts by its **threaded bushing through the `ENC_HOLE_D` panel hole + its own nut** (no posts); the Arduino sits on 4 short posts with **M2 self-tap** pilots (`ARD_PILOT_*`). See `cad/README.md` §6.
- **Design intent** (e.g. 12V into the board's DC barrel jack feeding VIN, fans tap VIN; cabinet-exhaust airflow; no resistors because TACH uses internal pullup and DS18B20 is a module with onboard 4.7k) is captured only in the READMEs — verify against it before "fixing" something that looks odd.

## Commands

CAD work is driven by the **`cad`** and **`cad-viewer`** agent skills (installed under `~/.agents/skills/`, with their own Python venv); `cad/README.md` also documents a plain build123d export path. All CAD commands run from `cad/`:

```bash
source ~/.agents/skills/cad/.venv/bin/activate
SKILL=~/.agents/skills/cad/scripts

python $SKILL/step rack_fan_2u.py                              # regenerate the full assembly STEP (for viewing only — not printed)
python $SKILL/step seg_right.py --force --stl stl/seg_right.stl # regenerate one printable part: STEP in cad/, STL into cad/stl/
python $SKILL/inspect refs rack_fan_2u.step --facts            # bounding box / warnings
python $SKILL/snapshot --input seg_right.step --output chk.png --display rendered --camera 220:32   # render (camera is azimuth:elevation; 'back' shows the true front)
```

Editing `rack_fan_2u.py`'s shared params means re-running `step` for **all four** printable parts (`seg_left/seg_mid/seg_right/encoder_knob`), since they import it.

CAD viewer (live review link):

```bash
node ~/.agents/skills/cad-viewer/scripts/viewer/backend/server.mjs --host 127.0.0.1 --dir "$(pwd)/cad" --shutdown-after 12h
# open http://127.0.0.1:<port>/?dir=<abs cad dir>&file=rack_fan_2u.step
```

Diagrams (need `matplotlib` + `Pillow`, e.g. the cad skill venv's python):

```bash
python3 tools/gen_breadboard.py    # rewrites tools/wiring.png (direct-to-Arduino wiring diagram)
python3 tools/gen_schematic.py     # rewrites tools/schematic.png
python3 tools/annotate_renders.py  # overlays English part labels onto cad/asm_assembled.png + asm_exploded.png — run AFTER re-snapshotting those two (it draws on top; running twice doubles the labels)
python3 tools/gen_oled_preview.py  # rewrites tools/oled_preview.png (OLED layout mockup, mirrors displayStep())
```

Firmware: flash from the Arduino IDE with the `Arduino UNO R4 Boards` core. A compile check works locally via `arduino-cli` (the sketch dir must be named `smartfan`; libraries live in the IDE's sketchbook):

```bash
arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi --libraries ~/Documents/Arduino/libraries firmware/smartfan
```

Only ArduinoJson v7 deprecation warnings are expected. install the libraries listed in `README.md` §6. There are no automated tests — verify the 25kHz fan PWM on hardware (`USE_PWMOUT_25K`, default on, via the core `PwmOut`); see `README.md` §6.

## CAD architecture (`cad/`)

- **`rack_fan_2u.py` is the single source of truth**: all parameters (top of file, mm, Z-up: X=width, Z=height, Y=depth-into-rack, origin = panel front center), all geometry helpers, device placeholders, and the assembled `gen_step()`. Full parameter reference and change-coupling notes are in **`cad/README.md`**.
- `seg_left.py` / `seg_mid.py` / `seg_right.py` are thin slices — each calls `make_segment()` to cut one X-band of the panel (the 482mm panel is split into 3 segments for the 256mm P1S bed, joined with M3 screws + tongue/groove). None of these three hold their own parameters.
- `encoder_knob.py` is the only standalone part (its own shaft-fit params); it's imported into the assembly.
- STEP is the primary artifact (kept beside its generator); printable STLs live in **`cad/stl/`** (print table in `README.md` §1.2). `asm_assembled.png` / `asm_exploded.png` are embedded in `README.md`; the `.*.step.glb` dotfiles are viewer caches.

## Firmware architecture (`firmware/smartfan/smartfan.ino`)

Single non-blocking `loop()`. The key design rule: **the temperature control loop runs entirely on the MCU and must keep cooling even if WiFi/MQTT/HA is down** — networking is an add-on, never a dependency of fan control.

- Control: fan curve (`Tset−10°C → DUTY_FLOOR`, `Tset+6°C → 100%`, linear between, ≤5%/s slew) with 4 modes (Auto / Manual / Silent-capped / Turbo) and failsafe (sensor lost or ≥`T_CRIT` → force 100% + alarm; high-duty-but-no-RPM → stall alarm).
- One 25kHz PWM on D9 (via the core `PwmOut` class, `pwm.h`; D9=GTIOC7A) shared by all three fans through the PST chain; the master fan's TACH on D2 is counted by interrupt. `USE_PWMOUT_25K 0` falls back to `analogWrite` (~490Hz). Single pin = single timer, avoids the R4 multi-pin same-timer pitfall.
- Display: 0.96" SSD1306 I²C OLED via `Adafruit_SSD1306`, drawn in `displayStep()` (layout mirrored by `tools/gen_oled_preview.py`); whole screen blinks on alarm.
- HA integration is MQTT auto-discovery (publishes `fan` / `sensor` (temp, rpm) / `binary_sensor` + a `climate` HVAC entity carrying the mode presets); HomeKit is reached by HA's HomeKit Bridge. `homeassistant/rack_fan.yaml` is a manual-YAML fallback for the same entities. Setpoint/mode/manual-% persist in EEPROM (`cfg`@0).
- **WiFi/MQTT are NOT hardcoded** — they're provisioned via a captive portal (`NetCfg`@EEPROM 512). First boot or reset (hold the encoder ~2s at power-on) → `runPortal()` scans WiFi (pre-AP, while still STA), opens AP `RackFan-Setup`, runs a tiny captive DNS (`dnsHandle()` answers every query with the AP IP via `WiFiUDP` on :53, so the phone auto-pops the page) + an HTTP form on :80, and the OLED shows a WiFi-join QR. The form (SSID picked from the scanned list — 2.4GHz only, since the R4 radio is 2.4GHz) writes WiFi/MQTT/device-ID, then `NVIC_SystemReset()`. The portal loop keeps calling `sampleStep()`/`controlStep()` every 1s, so cooling/failsafe never stop. Needs the `QRCode` (ricmoo) library; the DNS is hand-rolled (the ESP8266 `DNSServer` lib doesn't build on the R4 core).

## Documentation map

- `README.md` (English) + `README.zh-CN.md` (Chinese) — the user doc, one file per language: BOM (Taobao links) + print parts + fasteners, schematic + pinout, wiring (1-to-3 splitters + netlist), firmware flow / control algorithm / knob & OLED / provisioning / HA+HomeKit, assembly notes, flashing. Keep one file per language — don't split docs out; keep the two in sync. Images: the scripts render the **English** versions; `tools/fan_4pin_pinout.png` is the Chinese screenshot `fan_4pin_pinout_zh.png` with its text covered and re-lettered in English (no generator). `README.zh-CN.md` embeds static Chinese `*_zh.png` twins (`tools/schematic_zh.png`, `wiring_zh.png`, `oled_preview_zh.png`, `fan_4pin_pinout_zh.png`, `cad/asm_assembled_zh.png`, `asm_exploded_zh.png`) that the generators do NOT produce — when an image's content changes, the `_zh` twin is stale and must be updated too.
- `cad/README.md` + `cad/README.zh-CN.md` — CAD parameter reference + regeneration commands (developer-only).
