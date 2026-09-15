#!/usr/bin/env python3
"""Overlay part labels (text box + leader line) onto cad/asm_assembled.png and cad/asm_exploded.png.

Workflow: first re-render both images with the cad skill's snapshot script (display "rendered",
camera 220:32, 1600x1200; the exploded one with {"exploded": {"enabled": true, "axis": "y",
"spacing": 1.2}}), then run this script.
WARNING: this script overwrites the images in place. It assumes the input is a *clean* render;
    running it twice stacks two layers of labels.
    Label coordinates are hand-tuned for the 220:32 camera framing (pixel coordinates on a
    1600x1200 image); changing the camera means re-tuning them.
Note: the view looks at the panel from *behind* (+Y), so left/right are mirrored relative to the
front view -- the right segment (control area) appears on the left side of the image.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (text, arrow target (x,y), text position (x,y), horizontal alignment) -- pixel coords on 1600x1200
ASSEMBLED = [
    ("Right panel segment\nseg_right",   (450, 300),  (680, 145),  "center"),
    ("Middle panel segment\nseg_mid",    (830, 480),  (940, 260),  "center"),
    ("Left panel segment\nseg_left",     (1290, 660), (1400, 430), "center"),
    ("Fan 1 (master, TACH)",             (530, 610),  (400, 860),  "center"),
    ("Fan 2",                            (870, 730),  (740, 980),  "center"),
    ("Fan 3",                            (1210, 840), (1120, 1090), "center"),
    ("Arduino UNO R4 WiFi\n(flipped, headers facing back)", (265, 395), (15, 170),  "left"),
    ("OLED module\n(behind display window)", (295, 300), (460, 65),  "center"),
    ("DS18B20 module\n(holder)",         (357, 528),  (180, 700),  "center"),
    ("DC plug (placeholder)",            (100, 300),  (20, 570),   "left"),
]

EXPLODED = [
    ("Right panel segment\nseg_right",   (500, 300),  (330, 130),  "center"),
    ("Middle panel segment\nseg_mid",    (990, 470),  (1010, 250), "center"),
    ("Left panel segment\nseg_left",     (1330, 560), (1420, 330), "center"),
    ("Fan 1 (master, TACH)",             (435, 680),  (330, 950),  "center"),
    ("Fan 2",                            (755, 750),  (650, 1010), "center"),
    ("Fan 3",                            (1070, 820), (990, 1070), "center"),
    ("Arduino UNO R4 WiFi",              (185, 560),  (110, 320),  "left"),
    ("Encoder + knob",                   (740, 315),  (900, 170),  "center"),
    ("OLED module",                      (505, 330),  (620, 210),  "center"),
    ("DS18B20 module",                   (712, 408),  (860, 470),  "center"),
]


def annotate(png, items):
    img = Image.open(png)
    w, h = img.size
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(img)
    ax.set_xlim(0, w); ax.set_ylim(h, 0); ax.axis("off")
    for text, xy, xytext, ha in items:
        ax.annotate(text, xy=xy, xytext=xytext, ha=ha, va="center",
                    fontsize=15, color="#1a1a1a", linespacing=1.25,
                    bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#8a8a8a", lw=0.8, alpha=0.92),
                    arrowprops=dict(arrowstyle="-", color="#d97706", lw=1.6,
                                    shrinkA=2, shrinkB=1))
    fig.savefig(png, dpi=100)
    plt.close(fig)
    print("annotated", png)


annotate(os.path.join(ROOT, "cad", "asm_assembled.png"), ASSEMBLED)
annotate(os.path.join(ROOT, "cad", "asm_exploded.png"), EXPLODED)
