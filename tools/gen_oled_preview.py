#!/usr/bin/env python3
"""0.96" OLED (128x64) layout preview - pixel-level render using the firmware's
displayStep() coordinates and a 5x7 font.
Two screens: normal state / knob-adjust state."""
import math, os
import matplotlib
from PIL import Image, ImageDraw, ImageFont

G = {
 '0':"01110 10001 10011 10101 11001 10001 01110",
 '1':"00100 01100 00100 00100 00100 00100 01110",
 '2':"01110 10001 00001 00010 00100 01000 11111",
 '3':"11111 00010 00100 00010 00001 10001 01110",
 '4':"00010 00110 01010 10010 11111 00010 00010",
 '5':"11111 10000 11110 00001 00001 10001 01110",
 '6':"00110 01000 10000 11110 10001 10001 01110",
 '7':"11111 00001 00010 00100 01000 01000 01000",
 '8':"01110 10001 10001 01110 10001 10001 01110",
 '9':"01110 10001 10001 01111 00001 00010 01100",
 '.':"00000 00000 00000 00000 00000 01100 01100",
 '%':"11000 11001 00010 00100 01000 10011 00011",
 ' ':"00000 00000 00000 00000 00000 00000 00000",
 'A':"01110 10001 10001 11111 10001 10001 10001",
 'C':"01110 10001 10000 10000 10000 10001 01110",
 'D':"11110 10001 10001 10001 10001 10001 11110",
 'E':"11111 10000 10000 11110 10000 10000 11111",
 'F':"11111 10000 10000 11110 10000 10000 10000",
 'M':"10001 11011 10101 10101 10001 10001 10001",
 'N':"10001 11001 10101 10011 10001 10001 10001",
 'O':"01110 10001 10001 10001 10001 10001 01110",
 'P':"11110 10001 10001 11110 10000 10000 10000",
 'R':"11110 10001 10001 11110 10100 10010 10001",
 'S':"01111 10000 10000 01110 00001 00001 11110",
 'T':"11111 00100 00100 00100 00100 00100 00100",
 'U':"10001 10001 10001 10001 10001 10001 01110",
}
G = {k: v.split() for k, v in G.items()}

W, H = 128, 64

class Screen:
    def __init__(s): s.px = [[0]*W for _ in range(H)]
    def set(s, x, y):
        if 0 <= x < W and 0 <= y < H: s.px[y][x] = 1
    def frect(s, x, y, w, h):
        for dy in range(h):
            for dx in range(w): s.set(x+dx, y+dy)
    def drect(s, x, y, w, h):
        s.frect(x, y, w, 1); s.frect(x, y+h-1, w, 1)
        s.frect(x, y, 1, h); s.frect(x+w-1, y, 1, h)
    def line(s, x0, y0, x1, y1):
        dx, dy = abs(x1-x0), abs(y1-y0); sx = 1 if x0<x1 else -1; sy = 1 if y0<y1 else -1
        err = dx-dy
        while True:
            s.set(x0, y0)
            if x0==x1 and y0==y1: break
            e2 = 2*err
            if e2 > -dy: err -= dy; x0 += sx
            if e2 < dx: err += dx; y0 += sy
    def circ(s, cx, cy, r, fill=False):
        for dy in range(-r, r+1):
            for dx in range(-r, r+1):
                d = round(math.hypot(dx, dy))
                if (d <= r) if fill else (d == r): s.set(cx+dx, cy+dy)
    def ch(s, x, y, c, size):
        g = G.get(c, G[' '])
        for r in range(7):
            for col in range(5):
                if g[r][col] == '1': s.frect(x+col*size, y+r*size, size, size)
    def text(s, x, y, t, size):
        for c in t: s.ch(x, y, c, size); x += 6*size
    # Icons (match the firmware)
    def thermo(s, x, y): s.drect(x-2, y, 5, 13); s.frect(x-1, y+6, 3, 9); s.circ(x, y+15, 4, True)
    def fan(s, cx, cy):
        s.circ(cx, cy, 5); s.circ(cx, cy, 1, True)
        s.line(cx, cy, cx+3, cy-3); s.line(cx, cy, cx-3, cy+3); s.line(cx, cy, cx+3, cy+2)
    def wifi(s, nb):
        for i in range(4):
            bx, bh = 2+i*4, 3+i*2; by = 12-bh
            (s.frect if i < nb else s.drect)(bx, by, 3, bh)

def topbar(s, mode, nb=4, alarm=False, wifi_ok=True):
    s.wifi(nb)
    if not wifi_ok: s.text(21, 4, "x", 1)
    if alarm: s.text(40, 4, "ALM", 1)
    s.text(W - len(mode)*6, 4, mode, 1)
    s.frect(0, 15, W, 1)

def screen_normal(temp=26.8, mode="AUTO", rpm=1850, duty=60):
    s = Screen(); topbar(s, mode)
    s.thermo(8, 22)
    t = f"{temp:.1f}"; s.text(22, 22, t, 3)
    ex = 22 + len(t)*18; s.circ(ex+3, 25, 2); s.text(ex+8, 28, "C", 2)
    s.fan(8, 56)
    s.text(20, 53, f"{rpm} RPM", 1)
    ds = f"{duty}%"; s.text(W - len(ds)*6, 53, ds, 1)
    return s

def screen_edit(setp=35, mode="AUTO", rpm=1850, duty=60):
    s = Screen(); topbar(s, mode)
    s.text(6, 17, "SET", 1)                       # label
    v = str(setp); s.text(6, 27, v, 2)            # value (2x font, sits high so it doesn't crowd the bottom row)
    ex = 6 + len(v)*12; s.circ(ex+2, 29, 2); s.text(ex+6, 27, "C", 2)
    s.fan(8, 56)                                  # bottom status row shown as usual
    s.text(20, 53, f"{rpm} RPM", 1)
    ds = f"{duty}%"; s.text(W - len(ds)*6, 53, ds, 1)
    return s

# ---- Render ----
SC = 7; GAP = 1
BG = (10, 14, 22); FG = (210, 232, 255); PANEL = (4, 6, 10)

def render(s):
    img = Image.new("RGB", (W*SC, H*SC), BG)
    d = ImageDraw.Draw(img)
    for y in range(H):
        for x in range(W):
            if s.px[y][x]:
                d.rectangle([x*SC, y*SC, x*SC+SC-1-GAP, y*SC+SC-1-GAP], fill=FG)
    return img

panels = [("Normal", screen_normal()), ("Adjusting (turning the knob)", screen_edit())]
pad, gap, labelh = 16, 28, 36
pw, ph = W*SC, H*SC
out = Image.new("RGB", (pad*2 + pw*2 + gap, pad + labelh + ph + pad), (235, 238, 242))
dd = ImageDraw.Draw(out)
try: font = ImageFont.truetype(os.path.join(matplotlib.get_data_path(), "fonts/ttf/DejaVuSans.ttf"), 20)
except Exception: font = ImageFont.load_default()
for i, (lab, s) in enumerate(panels):
    x0 = pad + i*(pw+gap); y0 = pad+labelh
    dd.rectangle([x0-3, y0-3, x0+pw+2, y0+ph+2], outline=(120,130,140), width=2)
    out.paste(render(s), (x0, y0))
    dd.text((x0, pad+2), lab, fill=(40,44,50), font=font)
_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oled_preview.png")
out.save(_OUT)
print("saved", _OUT, out.size)
