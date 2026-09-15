# CAD sources (build123d, parametric)

**English** | [简体中文](README.zh-CN.md)

The full assembly and every printed part are generated parametrically by these Python scripts. Change a parameter → regenerate → the STEP files (this directory) and STL files (`stl/`) update together.

## 1. File relationships

```
rack_fan_2u.py        main file: all parameters + geometry helpers + full assembly gen_step()
   ├─ seg_left.py     thin wrapper → make_segment() cuts the left segment    (no own parameters)
   ├─ seg_mid.py      thin wrapper → make_segment() cuts the middle segment  (no own parameters)
   ├─ seg_right.py    thin wrapper → make_segment() cuts the right segment   (no own parameters)
   └─ encoder_knob.py standalone knob part with its own parameters; imported into the assembly by the main file
```

- **Printed-part dimensions and hole positions → almost all live in the parameter block at the top of `rack_fan_2u.py`.** The 3 thin wrappers only "cut one piece out of the full assembly" and carry no parameters.
- Any change to `rack_fan_2u.py` means regenerating all 4 printed parts (they import it).
- Only the knob's shaft fit is tuned separately, in `encoder_knob.py`.

## 2. Coordinate system (Z-up)

Origin = **center of the panel front face**. `X` = width (+ is right), `Z` = height (+ is up), `Y` = depth (+Y points behind the panel).
CAD Viewer is Z-up as well. `rack_fan_2u.step` is the **full assembly** (including fan/Arduino placeholders), for viewing only — it is **not printed**.

## 3. How to generate

Each script exposes a `gen_step()` that returns a build123d shape. Run all commands from `cad/`.

### Option A: with the `cad` agent skill

If you use the `cad` agent skill (with its venv set up):

```bash
source ~/.agents/skills/cad/.venv/bin/activate
SKILL=~/.agents/skills/cad/scripts

# Full assembly (for viewing)
python $SKILL/step rack_fan_2u.py

# Individual printed parts: STEP (this directory) + STL (into stl/)
python $SKILL/step seg_right.py        --force --stl stl/seg_right.stl
python $SKILL/step seg_left.py         --force --stl stl/seg_left.stl
python $SKILL/step seg_mid.py          --force --stl stl/seg_mid.stl
python $SKILL/step encoder_knob.py     --force --stl stl/encoder_knob.stl
```

### Option B: plain build123d

```bash
pip install build123d
```

Then, from `cad/`:

```python
import importlib
from build123d import export_step, export_stl

# Printed parts: STEP + STL
for name in ["seg_left", "seg_mid", "seg_right", "encoder_knob"]:
    shape = importlib.import_module(name).gen_step()
    export_step(shape, f"{name}.step")
    export_stl(shape, f"stl/{name}.stl")

# Full assembly (for viewing only, no STL needed)
import rack_fan_2u
export_step(rack_fan_2u.gen_step(), "rack_fan_2u.step")
```

> After changing shared parameters in `rack_fan_2u.py`, **regenerate all 4 printed parts**; if you only changed `encoder_knob.py`, just regenerate the knob (and the assembly).

## 4. `rack_fan_2u.py` parameters (all at the top of the file, in mm)

### Panel / rack
| Parameter | Default | Meaning / effect of changing |
|---|---|---|
| `PANEL_W, PANEL_T, PANEL_H` | 482.6, 3.0, 88.1 | 19" 2U panel width / thickness / height (EIA-310; don't change width or height) |
| `RACK_HOLE_DX` | 465.1/2 | Half the distance between left and right rack hole centers |
| `RACK_HOLE_Z` | 38.1 | Rack hole Z per side (symmetric ±38.1) |
| `RACK_SLOT_LEN, RACK_SLOT_H` | 11.0, 7.0 | Rack oblong slot X length / Z height (length − height = ±2mm side-to-side play, M6) |

### Fans
| Parameter | Default | Meaning / effect of changing |
|---|---|---|
| `FAN` | 80.0 | Fan size (8025) |
| `FAN_BORE_D` | 76.0 | Panel air inlet cutout diameter |
| `FAN_HOLE_PITCH` | 71.5 | Square spacing of the 4 M4 screw holes |
| `FAN_HOLE_D` | 4.5 | M4 clearance hole diameter |
| `FAN_DEPTH` | 25.0 | Fan thickness (placeholder only) |
| `FAN_CX` | [-144, -29, 86] | **X centers of the 3 fans.** Changing this moves the whole layout; together with `CTRL_CX` it sets the 4 evenly spaced columns |

### Control column: OLED window / knob / Arduino / connectors
| Parameter | Default | Meaning / effect of changing |
|---|---|---|
| `CTRL_CX` | 174.0 | **Control column X center** (the OLED window is centered on it). Note that `ARD_CX`, `ENC_CX` and `SENS_CX` are set separately — update them as needed when changing `CTRL_CX` |
| `ARD_CX` | 165.0 | **Arduino X center** (9 left of `CTRL_CX`): clearance for the DC jack/plug on the right; **any further left hits fan 1 (master)** (left posts ≈ X133, fan 1 right edge X126) |
| `ARD_CZ` | 14.0 | Arduino Z center (mounted flipped; onboard matrix faces inward and is unused, so no window alignment needed) |
| `OLED_CZ` | 14.0 | OLED window + module Z center |
| `OLED_WIN_W, OLED_WIN_H` | 25.0, 13.5 | OLED window in the panel; window center `OLED_WIN_CZ` = `OLED_CZ` + 0.75 |
| `OLED_MOD_W/_T/_H` | 26.0, 5.0, 26.0 | OLED module PCB outline (placeholder + sets the size of the rear pocket) |
| `OLED_PIN_H` | 8.5 | OLED 4-pin header protrusion (wires exit toward +Y) |
| `OLED_HOLE_DX` | 10.5 | X of the OLED corner holes relative to board center (±10.5; measured 25×25 board, 2.0 from each side) |
| `OLED_HOLE_DZ_TOP, _BOT` | 11.0, -10.5 | Z of top/bottom holes relative to board center (top 1.5 from top edge, bottom 2.0 from bottom edge) |
| `OLED_STANDOFF_H` | 2.0 | Height of the 4 short OLED posts (glass close to the window; tune to the actual glass height) |
| `OLED_STANDOFF_D` | 4.5 | OLED post outer diameter (M2) |
| `OLED_PILOT_D, OLED_PILOT_DEPTH` | 2.0, 4.0 | M2 self-tap pilot hole in the OLED post tops (may extend into the panel) |
| `ENC_CX, ENC_CZ` | 174.0, -26.0 | Encoder (knob/shaft) center, below the OLED window (moved down so the KY-040 pins clear the Arduino posts) |
| `ENC_HOLE_D` | 7.2 | Clearance hole ⌀7.2 for the encoder's threaded bushing |
| `ARD_W, ARD_T, ARD_L` | 68.6, 1.6, 53.4 | UNO R4 board width / thickness / length (placeholder) |
| `ARD_STANDOFF_H` | 28.0 | Arduino post height: flipped, the solder side faces the panel and must clear the OLED module + pins/wires in front |
| `HDR_H` | 8.5 | Arduino female header height (faces backward when flipped; placeholder, sets the dupont-wire clearance) |
| `STANDOFF_D` | 8.0 | Arduino post outer diameter Ø8 |
| `ARD_PILOT_D, ARD_PILOT_DEPTH` | 2.0, 8.0 | **M2 self-tap pilot holes in the tops** of the 4 short Arduino posts (board holes Ø3.2 take M2) |
| `ARD_HOLES` | see file | **(x, z) of the 4 mounting holes relative to board center.** Currently the **flipped** version (component side / female headers toward +Y at the rear, USB/DC short edge still toward +X). If you change the board orientation, the hole positions must flip with it (see §6). |
| `DC_JACK_D/LEN`, `DC_PLUG_D/LEN`, `USB_*`, `CONN_DC_Z/USB_Z` | see file | Placeholders for the DC barrel jack / representative straight plug / USB-C on the port edge, **only for checking plug clearance** — not structural |

> ⚠️ **Two key orientation constraints**: (1) component side / female headers face **+Y (rear)** — otherwise there is no room for dupont wires; (2) the USB/DC short edge faces **+X (toward the panel's open right end)** — otherwise the DC plug can't go straight into the barrel jack. See the root `README.md` → "Assembly", step 4.

> 🔌 **Direct wiring**: the OLED/DS18B20/KY-040 connect directly to the Arduino via two 1-to-3 dupont splitter cables (one for 5V, one for GND); there is no breakout board, tray or other carrier on the panel.

### Sensor / cabling
| Parameter | Default | Meaning |
|---|---|---|
| `SENS_CX, SENS_CZ` | 145.0, -33.0 | DS18B20 module cradle center (free space below the control area) |
| `MOD_W, MOD_H, MOD_T` | 28.2, 13.0, 4.0 | DS18B20 PCB module outline (measured; sets the cradle size) |
| `SENS_HOLE_DX` | 6.4 | Sensor board mounting hole distance from the left edge (vertically centered); M2.5 self-tap hole in the cradle base |
| `SENS_PILOT_D` | 2.2 | M2.5 self-tap pilot hole diameter |
| `VENT_ZS` | () | Control-area vent slots (empty = none; if added, keep clear of the ⌀16 knob at `ENC_CZ`) |
| `CABLE_TIE_X` | () | Cable-tie holes along the bottom edge (empty = none) |

### Segmented printing + M3 joints
| Parameter | Default | Meaning / effect of changing |
|---|---|---|
| `SEAM1, SEAM2` | -86.5, 28.5 | **X of the two seams.** Must fall in the solid area between fans, and each segment must be ≤ 256 wide (P1S bed) |
| `WALL_T` | 6.0 | Joint wall thickness per side (X) |
| `WALL_Y0, WALL_Y1` | 3.0, 18.0 | Y range of the joint walls behind the panel (15mm deep) |
| `WALL_Z` | 84.0 | Joint wall height (nearly full height) |
| `GROOVE_W, GROOVE_D` | 4.0, 2.2 | Alignment tongue/groove width in Y / depth in X (tongue clearance is applied automatically) |
| `BOLT_YS, BOLT_ZS` | (6,15), (-28,28) | Y and Z positions of the 4 M3 bolts per seam (two rows, either side of the tongue/groove) |
| `M3_CLEAR_R` | 1.75 | M3 clearance hole radius (⌀3.5) |

## 5. `encoder_knob.py` parameters (standalone knob)

| Parameter | Default | Meaning / effect of changing |
|---|---|---|
| `SHAFT_D` | 6.0 | Encoder **shaft diameter** (round). Match your part |
| `SHAFT_FLAT_ACROSS` | 4.8 | D-shaft thickness **from the flat to the opposite side**. Match your part |
| `SHAFT_EXPOSED` | 14.0 | Shaft length proud of the panel front face with the nut tightened. Sets the bore depth and knob height |
| `FIT_CLEAR` | 0.3 | Bore print clearance (0.2~0.4; increase if too tight) |
| `TIP_CLEAR` | 0.5 | Gap between shaft tip and bore bottom, so the knob seats on the panel rather than on the shaft tip |
| `NUT_BORE_D, NUT_BORE_H` | 12.2, 3.0 | Bottom counterbore diameter / depth that clears the M7 mounting nut (KY-040 has no washer) |
| `KNOB_D` | 16.0 | Knob outer diameter (minimum set by `NUT_BORE_D`; wall around the counterbore ≈ 1.9mm) |
| `BORE_DEPTH` | 14.5 (derived) | Bore depth from the bottom face = `SHAFT_EXPOSED` + `TIP_CLEAR` |
| `TOP_WALL` | 2.5 | Top wall thickness above the bore (1.5mm solid remains under the indicator line) |
| `KNOB_H` | 17.0 (derived) | Knob height = `BORE_DEPTH` + `TOP_WALL` |
| `N_FLUTE, FLUTE_D` | 14, 2.2 | Number of side grip flutes / flute diameter (cut only above the counterbore) |
| `IND_W, IND_DEPTH` | 1.4, 1.0 | Top indicator line width / depth |

> If you switch to a different encoder, mainly check `SHAFT_D` / `SHAFT_FLAT_ACROSS` (round diameter and D-flat) and `SHAFT_EXPOSED`; if the knob won't press on, increase `FIT_CLEAR`.

## 6. Change-coupling reminders

1. **Moving the control column**: if you change `CTRL_CX`, update `ENC_CX` (defaults to the same 174) and `SENS_CX` (independent, 145) as needed, and check that the right rack slot (X = `RACK_HOLE_DX` ≈ 232.6) isn't hit.
2. **Arduino mounting orientation**: in `gen_step` the Arduino is flipped with `Rot(180,0,0)` (component side / female headers toward +Y at the rear, solder side toward the panel), and `ARD_HOLES` is flipped to match. That is why the front display is an **OLED** (`OLED_*` parameters + `Adafruit_SSD1306` in the firmware) instead of the onboard matrix. If you change the orientation, change all of these together.
   - When flipped, the posts must be tall enough (`ARD_STANDOFF_H`) to clear the OLED + pins in front — the female headers face backward, so dupont wires plug in directly.
3. **Seams**: `SEAM1/SEAM2` must fall in the solid area between fans, and each segment must be ≤ 256mm.
4. After any change, always **regenerate and visually inspect in the viewer** (especially hole positions and clearances) — passing deterministic checks doesn't mean nothing collides.
