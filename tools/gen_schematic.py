#!/usr/bin/env python3
"""2U smart temperature-controlled fan - schematic.

The layout keeps wire crossings to a minimum:
  - every signal line runs to the Arduino on the LEFT, one row each -> straight
    horizontal lines that never cross;
  - every power line runs to the RIGHT onto three vertical rails (GND / +5V / +12V).
Convention: a solid dot = junction (connected); lines crossing WITHOUT a dot = not connected.
"""
import os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

# Net colors
C12 = "#d32f2f"; C5 = "#f57c00"; CG = "#455a64"; CPWM = "#1565c0"; CTAC = "#2e7d32"
CDQ = "#7b1fa2"; CENC = "#00838f"; COLED = "#c2185b"

fig, ax = plt.subplots(figsize=(20, 13.6)); ax.set_xlim(0, 200); ax.set_ylim(-6, 128)
ax.set_aspect("equal"); ax.axis("off")

def wire(pts, color, lw=2.2, ls="-"):
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw, ls=ls,
            solid_capstyle="round", solid_joinstyle="round", zorder=2)

def dot(x, y, color="#222"):
    ax.add_patch(Circle((x, y), 1.05, fc=color, ec="white", lw=0.6, zorder=8))

def box(x0, y0, x1, y1, title, fc, sub="", tcol="#222"):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0.3,rounding_size=2",
                 facecolor=fc, edgecolor="#90a4ae", lw=1.4, zorder=3))
    ax.text((x0 + x1) / 2, y1 - 2.6, title, ha="center", va="top", fontsize=10.5,
            fontweight="bold", color=tcol, zorder=5)
    if sub:
        ax.text((x0 + x1) / 2, y1 - 6.4, sub, ha="center", va="top", fontsize=7.6,
                color=(tcol if tcol != "#222" else "#777"), zorder=5)

ax.text(100, 124, "2U Smart Rack Fan - Schematic", ha="center", fontsize=15, fontweight="bold", color="#222")
ax.text(100, 119.5, "Signals → left (one row each, straight lines); power → right (three vertical rails).   "
        "● = connected; crossing without a dot = not connected",
        ha="center", fontsize=9, color="#666")

# ---- Power rails (right, vertical) ----
RX = {"GND": 150, "+5V": 162, "+12V": 174}; RC = {"GND": CG, "+5V": C5, "+12V": C12}
RAIL_Y0, RAIL_Y1 = 12, 114
for n, x in RX.items():
    ax.plot([x, x], [RAIL_Y0, RAIL_Y1], color=RC[n], lw=3.0, zorder=1)
    ax.text(x, RAIL_Y1 + 2.4, n, color=RC[n], fontsize=11, fontweight="bold", ha="center")

# ---- Arduino (left) ----
AX0, AX1, AY0, AY1 = 8, 44, 24, 114
box(AX0, AY0, AX1, AY1, "Arduino UNO R4 WiFi", "#0d6e6e", "RA4M1 + ESP32-S3", "white")
ax.text((AX0 + AX1) / 2, AY1 + 2.4, "WiFi/MQTT → HA → HomeKit", ha="center", fontsize=8,
        color="#0d6e6e", fontstyle="italic")
# Signal pins on the right edge (y aligned with the matching component pin -> horizontal, no crossings)
AP = {"SCL": 111, "SDA": 107, "D3": 95, "D6": 91, "D12": 87, "D4": 77,
      "D2": 64, "D9": 46}
APC = {"SCL": COLED, "SDA": COLED, "D3": CENC, "D6": CENC, "D12": CENC, "D4": CDQ,
       "D2": CTAC, "D9": CPWM}
for nm, y in AP.items():
    ax.plot([AX1, AX1 + 2], [y, y], color=APC[nm], lw=2.6, zorder=4)
    ax.text(AX1 - 1.6, y, nm, color="white", fontsize=7, fontweight="bold", ha="right", va="center", zorder=6)

# ---- Components (middle column): signal pins on the LEFT, power pins on the RIGHT ----
CX0, CX1 = 80, 118; SX = CX0 - 2; PX = CX1 + 2
def comp(y0, y1, title, sub, fc, sig, pwr):
    box(CX0, y0, CX1, y1, title, fc, sub)
    for nm, col, y in sig:                                  # left: signal (to the Arduino)
        ax.plot([SX, CX0], [y, y], color=col, lw=2.4, zorder=4)
        ax.text(CX0 + 1.5, y, nm, color=col, fontsize=6.6, fontweight="bold", ha="left", va="center", zorder=6)
    for nm, rail, col, y in pwr:                            # right: to a power rail
        ax.plot([CX1, PX], [y, y], color=col, lw=2.4, zorder=4)
        ax.text(CX1 - 1.5, y, nm, color=col, fontsize=6.6, fontweight="bold", ha="right", va="center", zorder=6)
        wire([(PX, y), (RX[rail], y)], col, 2.0); dot(RX[rail], y, col)

comp(102, 115, "OLED 0.96\"", "SSD1306 · I²C", "#fce4ec",
     [("SCL", COLED, 111), ("SDA", COLED, 107)],
     [("VCC", "+5V", C5, 110), ("GND", "GND", CG, 105)])
comp(85, 98, "KY-040 encoder", "rotary knob", "#e0f2f1",
     [("CLK", CENC, 95), ("DT", CENC, 91), ("SW", CENC, 87)],
     [("+", "+5V", C5, 94), ("GND", "GND", CG, 88)])
comp(71, 82, "DS18B20", "module · onboard 4.7k", "#ede7f6",
     [("DQ", CDQ, 77)],
     [("VDD", "+5V", C5, 79), ("GND", "GND", CG, 74)])
# PST daisy-chain: PWM/12V/GND shared; only fan 1 (master) reports TACH -> D2
fan_rows = [(56, 68, "Fan 1 (master)", 64, 60, True), (42, 54, "Fan 2", None, 46, False), (28, 40, "Fan 3", None, 32, False)]
for (y0, y1, title, ytac, ypwm, has_tac) in fan_rows:
    sig = [("PWM", CPWM, ypwm)]
    if has_tac: sig.insert(0, ("TAC", CTAC, ytac))
    comp(y0, y1, title, "80mm · 4-pin", "#dbeafe", sig,
         [("12V", "+12V", C12, y1 - 2), ("GND", "GND", CG, y0 + 2)])

# ---- Direct signal wires: Arduino pin -> component signal pin (same height, horizontal) ----
for apin, col in [("SCL", COLED), ("SDA", COLED), ("D3", CENC), ("D6", CENC), ("D12", CENC),
                  ("D4", CDQ), ("D2", CTAC)]:
    y = AP[apin]; wire([(AX1 + 2, y), (SX, y)], col)
# D9 -> PWM fan-out to 3 fans (one line to all three pin-4s via a vertical bus)
BUSX = 72
wire([(AX1 + 2, AP["D9"]), (BUSX, AP["D9"])], CPWM)         # D9 -> bus
wire([(BUSX, 32), (BUSX, 60)], CPWM, 2.4)                   # vertical bus
for yp in (60, 46, 32):
    wire([(BUSX, yp), (SX, yp)], CPWM); dot(BUSX, yp, CPWM)  # bus -> each fan PWM

# ---- Power input: 12V adapter -> Arduino DC jack + +12V rail; Arduino 5V -> +5V rail ----
box(46, 1, 78, 10, "12V DC adapter", "#ffebee", "≥2A", "#b71c1c")
PN, GN = (78, 7), (78, 4)                                   # adapter + / - leads
# +12V: right to the +12V rail; left (same + net from the adapter's left edge) to the Arduino DC IN
wire([PN, (RX["+12V"], 7)], C12); dot(RX["+12V"], 7, C12)
wire([(46, 7), (12, 7), (12, AY0)], C12)
ax.plot([46, 78], [7, 7], color=C12, lw=2.2, zorder=2)      # + runs straight through the adapter (same net)
ax.text(12, AY0 + 1.6, "DC IN", color="white", fontsize=6.6, fontweight="bold", ha="center", va="bottom", zorder=6)
# Adapter GND -> GND rail
wire([GN, (RX["GND"], 4)], CG); dot(RX["GND"], 4, CG)
# Arduino 5V -> +5V rail
ax.text(30, AY0 + 1.6, "5V", color="white", fontsize=6.6, fontweight="bold", ha="center", va="bottom", zorder=6)
wire([(30, AY0), (30, 20), (RX["+5V"], 20)], C5); dot(RX["+5V"], 20, C5)
# Arduino GND -> GND rail
ax.text(38, AY0 + 1.6, "GND", color="white", fontsize=6.6, fontweight="bold", ha="center", va="bottom", zorder=6)
wire([(38, AY0), (38, 16), (RX["GND"], 16)], CG); dot(RX["GND"], 16, CG)

# ---- Notes ----
ax.text(100, -1.6,
        "+5V and GND each use one 1-to-3 dupont splitter to feed the 3 modules (OLED / DS18B20 / encoder); "
        "the fans take their own separate GND pin.",
        ha="center", va="center", fontsize=8, color="#555")
ax.text(100, -4.4,
        "PST daisy-chain: one 25kHz PWM from D9 + 12V + GND shared by all three fans; only the master fan reports TACH → D2. "
        "Fans run on +12V; the whole system shares one GND.",
        ha="center", va="center", fontsize=8, color="#555")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schematic.png")
fig.savefig(out, dpi=150, facecolor="white", bbox_inches="tight", pad_inches=0.3)
print("wrote", out)
