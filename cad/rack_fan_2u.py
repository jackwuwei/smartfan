# 19" 2U smart temperature-controlled fan -- full assembly model (build123d, Z-up)
#
# This revision: every module connects directly to the Arduino via two "1-to-3" dupont splitter cables.
# No base plate, so the airflow path is fully open.
#   - Arduino: 4 posts on the panel back (M2 self-tap pilot Ø2.0 in each post top; board holes Ø3.2 take M2),
#     mounted flipped so the female headers face backward for dupont wires.
#   - Modules (OLED/DS18B20/KY-040) each mount to the panel/posts; their pin headers wire straight to the Arduino.
#
# Coordinates (Z up): origin = center of the panel front face. X = width (+right), Z = height (+up),
# Y = depth (+Y = behind the panel).
from build123d import *
from encoder_knob import gen_step as _make_knob   # real knob geometry

# ---------------- Parameters (mm) ----------------
PANEL_W, PANEL_T, PANEL_H = 482.6, 3.0, 88.1
PANEL_BACK = PANEL_T
RACK_HOLE_DX = 465.1 / 2.0
RACK_HOLE_Z = 38.1                                      # 2 holes per side (upper/lower, symmetric ±38.1)
RACK_SLOT_LEN, RACK_SLOT_H = 11.0, 7.0                  # horizontal oblong slot: X length 11 (±2 play), Z height 7 (M6)

FAN = 80.0
FAN_BORE_D = 76.0
FAN_HOLE_PITCH = 71.5
FAN_HOLE_D = 4.5
FAN_DEPTH = 25.0
# 4 evenly spaced, centered columns: 3 fans + 1 control column, gaps ≈35mm, symmetric margins at the rack ears
FAN_CX = [-144.0, -29.0, 86.0]

# Control column (4th column): OLED window on top, knob below, stacked vertically; Arduino behind them
CTRL_CX = 174.0
ARD_CX = 165.0                                         # Arduino X center (9 left of CTRL_CX: clearance for the DC jack/plug on the right; any further left hits fan 1 (master))
ARD_CZ = 14.0                                          # Arduino center (flipped; onboard matrix faces inward, unused, no window alignment needed)
# Front display: 0.96" I2C OLED (SSD1306) -- with the Arduino flipped its onboard matrix faces inward, so an OLED is the front display
OLED_CZ = 14.0                                         # OLED module center (former LED window position)
OLED_WIN_W, OLED_WIN_H = 25.0, 13.5                    # display window (was 15 tall; trimmed 1.5 at the bottom -> top edge fixed, bottom edge raised)
OLED_WIN_CZ = OLED_CZ + 0.75                           # window center: 0.75 above module center, so the top edge stays put and only the bottom edge rises
OLED_MOD_W, OLED_MOD_T, OLED_MOD_H = 26.0, 5.0, 26.0   # OLED module PCB (placeholder; width X / thickness Y / height Z, 4-pin version)
OLED_PIN_H = 8.5                                       # 4-pin header protrusion (wires exit toward +Y)
# OLED 4 M2 mounting holes/posts (measured 25×25 module: Ø2 through-hole / Ø3.5 pad, 4 corners):
#   X 2.0 from left/right edges -> ±10.5 from board center; top holes 1.5 from top edge -> +11.0; bottom 2.0 from bottom edge -> −10.5 (board center = CTRL_CX, OLED_CZ)
OLED_HOLE_DX = 10.5
OLED_HOLE_DZ_TOP, OLED_HOLE_DZ_BOT = 11.0, -10.5
OLED_STANDOFF_H = 2.0                                  # OLED post height (short, glass close to window; tune to the actual glass height)
OLED_STANDOFF_D = 4.5                                  # OLED post outer diameter (M2; little room around the window)
OLED_PILOT_D, OLED_PILOT_DEPTH = 2.0, 4.0             # M2 self-tap pilot hole (may extend into the panel)
ENC_CX, ENC_CZ = 174.0, -26.0                          # encoder below the OLED window (moved −20 -> −26 so the KY-040 pins drop below the posts, clear of the Arduino posts)
ENC_HOLE_D = 7.2                                       # through-hole for the Ø6.8 threaded bushing (clearance; FDM holes print undersize)
# KY-040 mounting: threaded bushing through the Ø7.2 panel hole + the module's own nut (no extra posts/screw holes).

ARD_W, ARD_T, ARD_L = 68.6, 1.6, 53.4
ARD_STANDOFF_H = 28.0                   # raised (16 -> 28): flipped, the solder side faces the panel and must clear the OLED module + pins/wires in front
HDR_H = 8.5                             # Arduino female header height (faces backward when flipped, leaving room for dupont wires)
STANDOFF_D = 8.0                        # Arduino post outer diameter Ø8
# Arduino 4 short posts: M2 self-tapping screws (same as the proven Arduino_UNO_R4_WiFi_Hardcase; board holes Ø3.2 take M2).
# Pilot Ø2.0 (slightly enlarged; 1.7 was too tight; FDM shrinks it to ~1.8, M2 self-tap still forms threads); depth 8 (blind, post 28 tall, M2×6~8 works).
# ARD_HOLES verified against measurements of that hardcase's bottom shell: pairwise spacing error ≤0.1mm, an exact match.
ARD_PILOT_D, ARD_PILOT_DEPTH = 2.0, 8.0
# Arduino flipped: component side (female headers + onboard matrix + USB/DC ports) faces +Y (rear), so the headers
# face backward with room for dupont wires; solder side faces the panel. USB/DC still on the +X short edge, 12V still plugs straight into the jack (right-side gap unchanged).
# Relative to the "ports facing right" version, this flip is 180° about +X, so hole z values are negated.
ARD_HOLES = [(19.06, 24.1), (-31.74, 8.86), (-31.74, -19.08), (20.33, -24.16)]
# Connectors (drawn on the +X edge, to check straight-plug clearance)
DC_JACK_D, DC_JACK_LEN = 9.0, 11.0     # barrel jack Ø9, protrudes ~11mm
DC_PLUG_D, DC_PLUG_LEN = 12.0, 14.0    # representative straight plug (shows it is unobstructed)
USB_W, USB_H, USB_LEN = 9.0, 7.0, 6.0  # USB-C port
CONN_DC_Z, CONN_USB_Z = -6.0, 8.0      # Z of both ports on the short edge (both within the right-side post Z gap)

# (all modules wired directly to the Arduino via two "1-to-3" dupont splitter cables; no tray/long posts)

SENS_CX, SENS_CZ = 145.0, -33.0           # DS18B20 module position (free space below the control area, clear of fans/stack)
MOD_W, MOD_H, MOD_T = 28.2, 13.0, 4.0     # DS18B20 PCB 28.2×13 (measured); long edge = X (with header pins), on the open +Z side so pins are not blocked
SENS_HOLE_DX = 6.4                        # sensor board mounting hole: 6.4 from left edge (vertically centered), M2.5 self-tap
SENS_PILOT_D = 2.2                        # M2.5 self-tap pilot hole (in the cradle base plate)
VENT_ZS = ()                                  # control-area vent slots removed (empty = none)
CABLE_TIE_X = ()  # cable-tie holes all removed (none below the fans or in the control area)

# ---- Segmented printing (Bambu P1S, 256mm bed) + M3 screw/nut joints ----
SEAM1, SEAM2 = -86.5, 28.5     # seam X (in the solid area between fans)
WALL_T = 6.0                    # joint wall thickness per side (X)
WALL_Y0, WALL_Y1 = 3.0, 18.0   # joint wall: Y range behind the panel (15mm deep)
WALL_Z = 84.0                  # joint wall height (nearly full height)
GROOVE_W, GROOVE_D = 4.0, 2.2  # alignment tongue/groove: width in Y / depth in X
BOLT_YS = (6.0, 15.0)          # M3 bolt Y positions (one row each side of the tongue/groove)
BOLT_ZS = (-28.0, 28.0)        # M3 bolt Z positions
M3_CLEAR_R = 1.75              # M3 clearance hole radius (Ø3.5)


def cyl_y(x, z, r, length, y0=PANEL_T / 2):
    return Pos(x, y0, z) * Rot(90, 0, 0) * Cylinder(radius=r, height=length)


def slot_y(x, z, length_x, height_z, depth):
    """Horizontal oblong (stadium) slot: long axis along X, cut through the panel along Y."""
    r = height_z / 2.0
    straight = length_x - height_z
    s = Pos(x, PANEL_T / 2, z) * Box(straight, depth, height_z)
    for sx in (-straight / 2, straight / 2):
        s += Pos(x + sx, PANEL_T / 2, z) * Rot(90, 0, 0) * Cylinder(radius=r, height=depth)
    return s


def post_y(x, z, r, h, y_start):
    """Post along +Y, starting at y_start, length h."""
    return Pos(x, y_start + h / 2, z) * Rot(90, 0, 0) * Cylinder(radius=r, height=h)


def insert_bore_y(x, z, top_y, d, depth):
    """Post-top hole: Ø d, depth measured down from the post top (open at the top). Used for M2 self-tap pilots on the Arduino posts."""
    h = depth + 0.6
    yc = top_y - depth / 2 + 0.3
    return Pos(x, yc, z) * Rot(90, 0, 0) * Cylinder(radius=d / 2, height=h)


# ---------------- Device placeholders ----------------
def fan_placeholder():
    f = Box(FAN, FAN_DEPTH, FAN)
    f -= Rot(90, 0, 0) * Cylinder(radius=FAN_BORE_D / 2, height=FAN_DEPTH + 2)
    f += Rot(90, 0, 0) * Cylinder(radius=12, height=FAN_DEPTH)
    f += Box(FAN, 5, 5)
    f += Box(5, 5, FAN)
    return f


def arduino_placeholder():
    """Local frame: component side at −Y (onboard matrix + female headers + USB/DC ports). The assembly flips it 180° about X -> component side faces +Y."""
    cy = -(ARD_T / 2)                                                         # component side (local −Y)
    p = Box(ARD_W, ARD_T, ARD_L)
    p += Pos(0, cy - 0.5, 0) * Box(24, 1.0, 16)                               # onboard matrix (faces inward when flipped, illustrative)
    # female headers ×2 (along both long edges, component side; face backward when flipped, room for dupont wires)
    for zz in (ARD_L / 2 - 4, -(ARD_L / 2 - 4)):
        p += Pos(0, cy - HDR_H / 2, zz) * Box(ARD_W - 6, HDR_H, 2.6)
    xe = ARD_W / 2                                                            # +X port edge
    # DC barrel jack (opening toward +X) + representative straight plug (check: clear all the way to the panel end)
    p += Pos(xe + DC_JACK_LEN / 2, cy - 2, CONN_DC_Z) * Rot(0, 90, 0) * Cylinder(radius=DC_JACK_D / 2, height=DC_JACK_LEN)
    p += Pos(xe + DC_JACK_LEN + DC_PLUG_LEN / 2, cy - 2, CONN_DC_Z) * Rot(0, 90, 0) * Cylinder(radius=DC_PLUG_D / 2, height=DC_PLUG_LEN)
    p += Pos(xe + USB_LEN / 2, cy - 2, CONN_USB_Z) * Box(USB_LEN, USB_H, USB_W)   # USB-C port
    return p


def oled_placeholder():
    """0.96" OLED module: against the panel back, glass facing forward (−Y), 4-pin header toward +Y. Local origin = module center."""
    pcb = Box(OLED_MOD_W, OLED_MOD_T, OLED_MOD_H)
    glass = Pos(0, -(OLED_MOD_T / 2 + 0.6), 0) * Box(OLED_WIN_W - 1, 1.2, OLED_WIN_H - 1)
    pins = Pos(0, OLED_MOD_T / 2 + OLED_PIN_H / 2, OLED_MOD_H / 2 - 2) * Box(OLED_WIN_W, OLED_PIN_H, 2.6)
    return pcb + glass + pins


def encoder_placeholder():        # KY-040 module body + shaft (origin = shaft axis; knob is separate, see gen_step)
    body = Pos(0, PANEL_BACK + 4.5, 0) * Box(13, 9, 13)
    shaft = Pos(0, -6, 0) * Rot(90, 0, 0) * Cylinder(radius=3, height=16)   # measured: shaft tip at y=−14 (14mm proud of the panel front face)
    return body + shaft


# ---------------- Printed part: panel + Arduino posts + sensor cradle ----------------
def build_chassis():
    chassis = Pos(0, PANEL_T / 2, 0) * Box(PANEL_W, PANEL_T, PANEL_H)

    # Arduino posts ×4 (inside, M2 self-tap pilot in each top)
    for dx, dz in ARD_HOLES:
        chassis += post_y(ARD_CX + dx, ARD_CZ + dz, STANDOFF_D / 2, ARD_STANDOFF_H, PANEL_BACK)

    # OLED mounting posts ×4 (four corners around the window, M2 self-tap pilot in each top)
    for hx in (-OLED_HOLE_DX, OLED_HOLE_DX):
        for hz in (OLED_HOLE_DZ_TOP, OLED_HOLE_DZ_BOT):
            chassis += post_y(CTRL_CX + hx, OLED_CZ + hz, OLED_STANDOFF_D / 2, OLED_STANDOFF_H, PANEL_BACK)

    # DS18B20 module cradle (3-sided: base plate + two side walls (short edges) + end stop (−Z); module slides in from the open +Z side; then glue/cable tie)
    #   28.2×13 module: long edge (with header pins) on the open +Z side so the pins point up unobstructed; side walls grip the 13 short edges
    chassis += Pos(SENS_CX, PANEL_BACK + 1.5, SENS_CZ) * Box(MOD_W + 5, 3, MOD_H + 5)
    # side walls only grip the module's non-pin half (lower, −Z), shortened and moved down -> clear of the pins on the +Z long edge
    SW_LEN = 7.0                                                    # side wall length along Z (lower half only)
    sw_zc = SENS_CZ - (MOD_H / 2 + 1.5 - SW_LEN / 2)               # flush against the end stop, toward −Z
    for wx in (-(MOD_W / 2 + 1.5), MOD_W / 2 + 1.5):
        chassis += Pos(SENS_CX + wx, PANEL_BACK + 4, sw_zc) * Box(2, 7, SW_LEN)
    chassis += Pos(SENS_CX, PANEL_BACK + 4, SENS_CZ - (MOD_H / 2 + 1.5)) * Box(MOD_W + 5, 7, 2)  # end stop (−Z long edge)

    # (the former encoder anti-rotation posts ×2 were removed: on the left/right they blocked the KY-040 header pins; the encoder is held by its own threaded nut)

    # OLED pocket (shallow frame on the panel back: OLED drops in from behind, glass against the window, held with tape/glue; in front of the Arduino)
    od = OLED_MOD_T + 1.0
    chassis += (Pos(CTRL_CX, PANEL_BACK + od / 2, OLED_CZ) * Box(OLED_MOD_W + 4, od, OLED_MOD_H + 4)
                - Pos(CTRL_CX, PANEL_BACK + od / 2 + 1.2, OLED_CZ) * Box(OLED_MOD_W + 0.6, od, OLED_MOD_H + 0.6))

    # ---- Subtract: panel cutouts ----
    cutters = []
    for fx in FAN_CX:
        cutters.append(cyl_y(fx, 0, FAN_BORE_D / 2, PANEL_T + 4))
        for sx in (-FAN_HOLE_PITCH / 2, FAN_HOLE_PITCH / 2):
            for sz in (-FAN_HOLE_PITCH / 2, FAN_HOLE_PITCH / 2):
                cutters.append(cyl_y(fx + sx, sz, FAN_HOLE_D / 2, PANEL_T + 4))
    cutters.append(Pos(CTRL_CX, PANEL_T / 2, OLED_WIN_CZ) * Box(OLED_WIN_W, PANEL_T + 4, OLED_WIN_H))   # OLED window
    for hx in (-OLED_HOLE_DX, OLED_HOLE_DX):                          # OLED 4 post tops: M2 self-tap pilots
        for hz in (OLED_HOLE_DZ_TOP, OLED_HOLE_DZ_BOT):
            cutters.append(insert_bore_y(CTRL_CX + hx, OLED_CZ + hz, PANEL_BACK + OLED_STANDOFF_H, OLED_PILOT_D, OLED_PILOT_DEPTH))
    cutters.append(cyl_y(ENC_CX, ENC_CZ, ENC_HOLE_D / 2, PANEL_T + 4))                    # encoder hole (bushing passes through + its own nut)
    for sx in (-RACK_HOLE_DX, RACK_HOLE_DX):                          # rack: 2 horizontal oblong slots per side
        for sz in (-RACK_HOLE_Z, RACK_HOLE_Z):
            cutters.append(slot_y(sx, sz, RACK_SLOT_LEN, RACK_SLOT_H, PANEL_T + 4))
    for dx, dz in ARD_HOLES:                                          # Arduino 4 post tops: M2 self-tap pilots
        cutters.append(insert_bore_y(ARD_CX + dx, ARD_CZ + dz, PANEL_BACK + ARD_STANDOFF_H, ARD_PILOT_D, ARD_PILOT_DEPTH))
    # sensor board mounting hole: M2.5 self-tap in the cradle base (6.4 from board left edge, vertically centered; screw driven from the board back to clamp it)
    cutters.append(insert_bore_y(SENS_CX - MOD_W / 2 + SENS_HOLE_DX, SENS_CZ, PANEL_BACK + 3, SENS_PILOT_D, 4.0))
    for vz in VENT_ZS:                                                # control-area vent slots (convection for the electronics bay)
        cutters.append(Pos(CTRL_CX, PANEL_T / 2, vz) * Box(24, PANEL_T + 4, 2))
    for cx in CABLE_TIE_X:                                            # cable-tie holes (bottom edge, one pair each)
        for dxh in (-3, 3):
            cutters.append(cyl_y(cx + dxh, -41, 1.75, PANEL_T + 4))

    for c in cutters:
        chassis -= c
    return chassis


# ---------------- Render colors (affect STEP/snapshot appearance only) ----------------
COLOR_PRINT = Color(0.32, 0.32, 0.34)   # printed parts: black plastic (PETG, charcoal, keeps some shading contrast)
COLOR_FAN   = Color(0.46, 0.49, 0.53)   # fan placeholders: dark gray
COLOR_PCB   = Color(0.00, 0.52, 0.52)   # Arduino: teal (R4 color scheme)
COLOR_OLED  = Color(0.08, 0.12, 0.35)   # OLED module: dark blue PCB
COLOR_METAL = Color(0.62, 0.64, 0.68)   # encoder: metallic gray
COLOR_SENS  = Color(0.15, 0.35, 0.75)   # DS18B20 module: blue


# ---------------- Segments + M3 joints ----------------
def seam_wall(xs, side):
    """Joint wall at a seam: side='L' belongs to the left segment (X[xs-T,xs]), 'R' to the right segment (X[xs,xs+T]).
    The two walls face each other at xs; 4 M3 bolts pass through both walls along X (heads and nuts in the open space behind the panel);
    the tongue/groove keeps the front faces flush and aligned."""
    ymid = (WALL_Y0 + WALL_Y1) / 2
    yh = WALL_Y1 - WALL_Y0
    if side == "L":
        w = Pos(xs - WALL_T / 2, ymid, 0) * Box(WALL_T, yh, WALL_Z)
        w -= Pos(xs, ymid, 0) * Box(GROOVE_D * 2, GROOVE_W, WALL_Z + 2)          # groove
    else:
        w = Pos(xs + WALL_T / 2, ymid, 0) * Box(WALL_T, yh, WALL_Z)
        w += Pos(xs, ymid, 0) * Box((GROOVE_D - 0.25) * 2, GROOVE_W - 0.4, WALL_Z)  # tongue (slightly undersized for clearance)
    for by in BOLT_YS:
        for bz in BOLT_ZS:
            w -= Pos(xs, by, bz) * Rot(0, 90, 0) * Cylinder(radius=M3_CLEAR_R, height=2 * WALL_T + 8)
    return w


def make_segment(x0, x1, walls):
    """Take the part of the full printed chassis within X[x0,x1] and add the joint wall at each seam."""
    body = build_chassis() & (Pos((x0 + x1) / 2, 60, 0) * Box(x1 - x0, 240, 240))
    for xs, side in walls:
        body += seam_wall(xs, side)
    body.color = COLOR_PRINT
    return body


# ---------------- Assembly ----------------
def gen_step():
    parts = []

    half = PANEL_W / 2
    segL = make_segment(-half, SEAM1, [(SEAM1, "L")]); segL.label = "seg_left"
    segM = make_segment(SEAM1, SEAM2, [(SEAM1, "R"), (SEAM2, "L")]); segM.label = "seg_mid"
    segR = make_segment(SEAM2, half, [(SEAM2, "R")]); segR.label = "seg_right"
    parts += [segL, segM, segR]

    for i, fx in enumerate(FAN_CX):
        fan = Pos(fx, PANEL_BACK + FAN_DEPTH / 2, 0) * fan_placeholder()
        fan.label = f"fan_{['left', 'mid', 'right'][i]}"
        fan.color = COLOR_FAN
        parts.append(fan)

    # Arduino flipped: 180° about X -> component side/female headers face +Y (rear, for dupont wires), solder side faces the panel
    ard = Pos(ARD_CX, PANEL_BACK + ARD_STANDOFF_H + ARD_T / 2, ARD_CZ) * Rot(180, 0, 0) * arduino_placeholder()
    ard.label = "arduino_uno_r4_wifi"
    ard.color = COLOR_PCB
    parts.append(ard)

    oled = Pos(CTRL_CX, PANEL_BACK + OLED_STANDOFF_H + OLED_MOD_T / 2, OLED_CZ) * oled_placeholder()
    oled.label = "oled_096"
    oled.color = COLOR_OLED
    parts.append(oled)

    enc = Pos(ENC_CX, 0, ENC_CZ) * encoder_placeholder()
    enc.label = "rotary_encoder"
    enc.color = COLOR_METAL
    parts.append(enc)

    # Real knob: rotated onto the shaft axis (local +Z -> assembly −Y), bottom face against the panel front face (y=0; bottom counterbore clears the nut)
    knob = Pos(ENC_CX, 0, ENC_CZ) * Rot(90, 0, 0) * _make_knob()
    knob.label = "encoder_knob"
    knob.color = COLOR_PRINT
    parts.append(knob)

    sensor = Pos(SENS_CX, PANEL_BACK + 3 + MOD_T / 2, SENS_CZ) * Box(MOD_W, MOD_T, MOD_H)
    sensor.label = "ds18b20_module"
    sensor.color = COLOR_SENS
    parts.append(sensor)

    asm = Compound(children=parts)
    asm.label = "rack_fan_2u"
    return asm
