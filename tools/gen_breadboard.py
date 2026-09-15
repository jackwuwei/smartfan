#!/usr/bin/env python3
"""2U smart temperature-controlled fan - wiring diagram: every module connects directly
to the UNO R4 WiFi using two 1-to-3 dupont splitters.

Power distribution:
  - 5V  1-to-3 splitter: Arduino 5V  -> OLED VCC / DS18B20 VDD / KY-040 "+"
  - GND 1-to-3 splitter: Arduino GND -> OLED GND / DS18B20 GND / KY-040 GND
The fans (PST daisy-chain, master fan's 4-pin lead) and all signal lines plug straight
into the headers, not through a splitter:
  +12V -> VIN, fan GND -> a second GND pin, TACH (master fan only) -> D2, PWM -> D9.
Signal lines: OLED SDA/SCL -> onboard I2C pins, DS18B20 DQ -> D4,
KY-040 CLK -> D3 / DT -> D6 / SW -> D12.
No external resistors: TACH uses the internal pull-up and the DS18B20 module has an
onboard 4.7k; 12V enters through the onboard DC barrel jack -> VIN.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch

fig, ax = plt.subplots(figsize=(22, 14.5))
ax.set_xlim(0, 200); ax.set_ylim(0, 137); ax.set_aspect("equal"); ax.axis("off")

# ===== Colors =====
C12  ="#d32f2f"   # +12V
C5   ="#f57c00"   # +5V
CG   ="#303030"   # GND
CPWM ="#1565c0"   # PWM D9
CTAC ="#2e7d32"   # TACH D2
CDQ  ="#7b1fa2"   # 1-Wire DQ D4
CENC ="#00838f"   # encoder D3/D6/D12
COLED="#c2185b"   # OLED I2C SDA/SCL

def wire(pts,color,lw=2.0,z=5,ls="-"):
    ax.plot([p[0] for p in pts],[p[1] for p in pts],color=color,lw=lw,
            solid_capstyle="round",solid_joinstyle="round",zorder=z,ls=ls)
def dot(x,y,color="#222"):                       # junction (solid dot): connected
    ax.add_patch(Circle((x,y),0.9,facecolor=color,edgecolor="white",lw=0.5,zorder=14))

# ============================================================
# Arduino UNO R4 WiFi - real headers on both sides (left = power/analog, right = digital)
# ============================================================
AX0,AX1,AY0,AY1=18,60,40,118
ax.add_patch(FancyBboxPatch((AX0,AY0),AX1-AX0,AY1-AY0,
             boxstyle="round,pad=0.4,rounding_size=2",facecolor="#0d6e6e",
             edgecolor="#08504f",lw=1.5,zorder=3))
ax.text((AX0+AX1)/2,AY1-2.5,"Arduino UNO R4 WiFi",color="white",fontsize=11,
        fontweight="bold",ha="center",va="top",zorder=4)
ax.add_patch(Rectangle((30,AY1-0.2),9,4,facecolor="#bbb",edgecolor="#888",zorder=3))
ax.text(34.5,AY1+4.4,"USB-C",fontsize=6.5,ha="center",va="bottom")
# 12x8 LED matrix (board mounted flipped, faces inward, unused)
for r in range(8):
    for cc in range(12):
        ax.add_patch(Circle((30.5+cc*1.5,AY1-7.5-r*1.5),0.45,facecolor="#ff5252",edgecolor="none",zorder=4))
ax.text(39,AY1-7.5-8*1.5-0.8,"12×8 LED matrix\n(faces inward, unused)",color="white",fontsize=7,ha="center",va="top",zorder=4)

# Real header pins (y coordinate); right = digital, left = power/analog
right_pins=[("D19/SCL",110),("D18/SDA",107),("AREF",104),("GND",101),("D13",98),
            ("D12",95),("~D11",92),("~D10",89),("~D9",86),("D8",83),
            ("D7",79),("~D6",76),("~D5",73),("D4",70),("~D3",67),("D2",64),("D1/TX",61),("D0/RX",58)]
left_pins=[("OFF",110),("GND",107),("VRTC",104),("BOOT",101),("IOREF",98),("RESET",95),
           ("+3V3",92),("+5V",89),("GND",86),("GND",83),("VIN",79),
           ("A0",75),("A1",72),("A2",69),("A3",66),("A4",63),("A5",60)]

# Used pins -> color (y disambiguates the identically named GND pins)
used_right={("~D9",86):CPWM,("D2",64):CTAC,("D4",70):CDQ,("~D3",67):CENC,
            ("~D6",76):CENC,("D12",95):CENC,
            ("D19/SCL",110):COLED,("D18/SDA",107):COLED}
used_left={("+5V",89):C5,("VIN",79):C12,("GND",86):CG,("GND",83):CG}  # GND@86 -> module splitter, GND@83 -> fans

for lab,y in right_pins:
    col=used_right.get((lab,y))
    ax.plot([AX1,AX1+1.6],[y,y],color=col or "#7fb0b0",lw=2.6 if col else 1.4,zorder=4)
    ax.text(AX1-1.4,y,lab,color="white" if col else "#9fd0d0",
            fontsize=6 if col else 5.2,fontweight="bold" if col else "normal",ha="right",va="center",zorder=4)
for lab,y in left_pins:
    col=used_left.get((lab,y))
    ax.plot([AX0-1.6,AX0],[y,y],color=col or "#7fb0b0",lw=2.6 if col else 1.4,zorder=4)
    ax.text(AX0+1.4,y,lab,color="white" if col else "#9fd0d0",
            fontsize=6 if col else 5.2,fontweight="bold" if col else "normal",ha="left",va="center",zorder=4)
ax.text(AX1+2,113,"Digital headers →",fontsize=7,color="#08504f",ha="left",va="center",fontstyle="italic")
ax.text(AX0-2,113,"← Power / analog",fontsize=7,color="#08504f",ha="right",va="center",fontstyle="italic")

# x of the right-side pin tips
RPX=AX1+1.6
# x of the left-side pin tips
LPX=AX0-1.6

# ============================================================
# Module boxes along the top (signal + power pins face down)
# ============================================================
def comp_box(cx,w,ytop,h,title,sub,fc):
    ax.add_patch(FancyBboxPatch((cx-w/2,ytop-h),w,h,boxstyle="round,pad=0.3,rounding_size=1.5",
                 facecolor=fc,edgecolor="#90a4ae",lw=1.3,zorder=4))
    ax.text(cx,ytop-h*0.34,title,fontsize=9,fontweight="bold",ha="center",va="center",zorder=5)
    if sub: ax.text(cx,ytop-h*0.72,sub,fontsize=7,ha="center",va="center",color="#555",zorder=5)

def pin_label(cx,yb,lab,col):
    ax.text(cx,yb+0.6,lab,fontsize=6,color=col,ha="center",va="bottom",zorder=8)

# Shared module-box parameters
BOX_TOP=134; BOX_H=13; BOX_YB=BOX_TOP-BOX_H   # y where the pins start

# ---- OLED 0.96" I2C ----
OX=98
comp_box(OX,20,BOX_TOP,BOX_H,'OLED 0.96"',"SSD1306 I2C","#fce4ec")
o_vcc,o_gnd,o_sda,o_scl = OX-6.5, OX-2.2, OX+2.2, OX+6.5

# ---- DS18B20 ----
DX=128
comp_box(DX,18,BOX_TOP,BOX_H,"DS18B20 module","onboard 4.7k","#ede7f6")
d_vdd,d_gnd,d_dq = DX-5.5, DX-0.5, DX+5.0

# ---- KY-040 encoder ----
KX=162
comp_box(KX,26,BOX_TOP,BOX_H,"KY-040 encoder","rotary knob","#e0f2f1")
k_plus,k_gnd,k_clk,k_dt,k_sw = KX-10, KX-5.5, KX-1, KX+4.5, KX+9.5

# ============================================================
# Bottom right: fan group (PST daisy-chain)
# ============================================================
FAN_TOP=34; FAN_H=14
fan_xc=[150,168,186]
for i,fx in enumerate(fan_xc):
    comp_box(fx,15,FAN_TOP,FAN_H,"","","#dbeafe")
    if i==0:  # master fan: title shifted left to clear the TACH/PWM lines crossing the box; no rotor circle
        ax.text(147,FAN_TOP-2.2,"Fan 1",fontsize=9,fontweight="bold",ha="center",va="center",zorder=5)
        ax.text(147,FAN_TOP-5.2,"(master)",fontsize=7,ha="center",va="center",color="#555",zorder=5)
    else:
        ax.text(fx,FAN_TOP-2.2,f"Fan {i+1}",fontsize=9,fontweight="bold",ha="center",va="center",zorder=5)
        ax.add_patch(Circle((fx,FAN_TOP-FAN_H/2-2),2.6,facecolor="none",edgecolor="#3b82f6",lw=1.0,zorder=5))
ax.text((fan_xc[0]+fan_xc[-1])/2,FAN_TOP+5.2,"PST daisy-chain: 3× 80mm 4-pin, fans 2-3 share PWM/12V/GND (no TACH)",
        fontsize=8,ha="center",va="bottom",color="#1565c0",fontweight="bold")
# Master fan's 4 pins (labels below the box so the lines crossing it don't cover them)
f_yb=FAN_TOP-FAN_H
fx0=fan_xc[0]
f_g,f_12,f_tac,f_pwm = fx0-5.5, fx0-1.5, fx0+2.5, fx0+6
def fan_label(x,lab,col):
    ax.text(x,f_yb-0.8,lab,fontsize=6,color=col,ha="center",va="top",zorder=8)
# PST link sketch (fan 1 -> fan 2 -> fan 3 shared lines)
for a,b in zip(fan_xc[:-1],fan_xc[1:]):
    ya=FAN_TOP-FAN_H*0.5
    wire([(a+7.5,ya),(b-7.5,ya)],"#3b82f6",2.6)
    ax.text((a+b)/2,ya+0.6,"PST",fontsize=5.5,color="#3b82f6",ha="center",va="bottom")

# ============================================================
# 1-to-3 splitter nodes
# ============================================================
def splitter(nx,ny,color,title):
    """Small one-in/three-out junction block: 1 in on the left, 3 out on top. Returns (input point, three top outputs)."""
    w,h=11,6
    ax.add_patch(FancyBboxPatch((nx-w/2,ny-h/2),w,h,boxstyle="round,pad=0.2,rounding_size=1",
                 facecolor=color,edgecolor="#222",lw=1.3,zorder=9,alpha=0.95))
    ax.text(nx,ny,title,fontsize=7,fontweight="bold",color="white",ha="center",va="center",zorder=11)
    inp=(nx-w/2, ny)
    outs=[(nx-w*0.30, ny+h/2),(nx, ny+h/2),(nx+w*0.30, ny+h/2)]
    return inp, outs

# Two splitter nodes in the gap below the modules: x clears every module pin line, y keeps the output corridor below the box bottoms
S5X,S5Y = 113, 113   # 5V splitter (below, between OLED and DS18B20)
GS_X,GS_Y = 142.5, 113 # GND splitter (below, between DS18B20 and KY-040)

# ============================================================
# Signal lines + direct fan lines (drawn before the splitters so the splitters sit on top)
# Signal corridor y=100.8-108.5 (below the splitters); splitter output corridor y=117-120.5 (below box bottom 121)
# ============================================================
# --- OLED signals: SDA/SCL ---
wire([(o_sda,BOX_YB),(o_sda,107),(RPX,107)],COLED,2.0)                          # SDA -> D18 (straight across at the same height)
wire([(o_scl,BOX_YB),(o_scl,108.5),(RPX+8,108.5),(RPX+8,110),(RPX,110)],COLED,2.0)  # SCL -> D19
dot(RPX,107,COLED); dot(RPX,110,COLED)
pin_label(o_sda,BOX_YB,"SDA",COLED); pin_label(o_scl,BOX_YB,"SCL",COLED)

# --- DS18B20 signal: DQ -> D4 ---
wire([(d_dq,BOX_YB),(d_dq,106),(RPX+10,106),(RPX+10,70),(RPX,70)],CDQ,2.0)
dot(RPX,70,CDQ)
pin_label(d_dq,BOX_YB,"DQ",CDQ)

# --- KY-040 signals: CLK -> D3 / DT -> D6 / SW -> D12 ---
wire([(k_clk,BOX_YB),(k_clk,104.5),(RPX+14,104.5),(RPX+14,67),(RPX,67)],CENC,2.0)  # CLK -> D3
wire([(k_dt ,BOX_YB),(k_dt ,102),(RPX+16,102),(RPX+16,76),(RPX,76)],CENC,2.0)      # DT -> D6
wire([(k_sw ,BOX_YB),(k_sw ,100.8),(RPX+18,100.8),(RPX+18,95),(RPX,95)],CENC,2.0)  # SW -> D12
dot(RPX,67,CENC); dot(RPX,76,CENC); dot(RPX,95,CENC)
pin_label(k_clk,BOX_YB,"CLK",CENC); pin_label(k_dt,BOX_YB,"DT",CENC); pin_label(k_sw,BOX_YB,"SW",CENC)

# --- Fans: PWM -> D9, TACH (master) -> D2 ---
# Shared PWM: from the master fan's PWM pin back to D9
wire([(f_pwm,f_yb),(f_pwm,38),(RPX+22,38),(RPX+22,86),(RPX,86)],CPWM,2.2)
dot(RPX,86,CPWM)
fan_label(f_pwm,"PWM",CPWM)
# TACH from the master fan only: back to D2
wire([(f_tac,f_yb),(f_tac,36),(RPX+20,36),(RPX+20,64),(RPX,64)],CTAC,2.0)
dot(RPX,64,CTAC)
fan_label(f_tac,"TAC",CTAC)
# Fan +12V -> VIN (left side), routed around below the Arduino
wire([(f_12,f_yb),(f_12,28),(LPX-12,28),(LPX-12,79),(LPX,79)],C12,2.4)
dot(LPX,79,C12)
fan_label(f_12,"12V",C12)
# Fan GND -> its own GND pin on the board (left GND@83, dedicated)
wire([(f_g,f_yb),(f_g,25),(LPX-9,25),(LPX-9,83),(LPX,83)],CG,2.2)
dot(LPX,83,CG)
fan_label(f_g,"G",CG)

# ============================================================
# 5V splitter: Arduino 5V (left @89) -> OLED VCC / DS18B20 VDD / KY-040 +
# ============================================================
# In: 5V pin -> up the left side of the board, right along the corridor (y~103.2), then up to the splitter input
inp5,out5 = splitter(S5X,S5Y,C5,"5V 1→3")
wire([(LPX,89),(LPX-8,89),(LPX-8,103.2),(106,103.2),(106,S5Y),(inp5[0],inp5[1])],C5,2.4)
dot(LPX,89,C5)
# 3 outputs: first to a corridor below the boxes (y<121), then straight up to each module's power pin (crossing no box)
y5=[117.2, 118.5, 119.8]
for (ox,oy),tx,yy in zip(out5,(o_vcc,d_vdd,k_plus),y5):
    wire([(ox,oy),(ox,yy),(tx,yy),(tx,BOX_YB)],C5,2.0)
pin_label(o_vcc,BOX_YB,"VCC",C5); pin_label(d_vdd,BOX_YB,"VDD",C5); pin_label(k_plus,BOX_YB,"+",C5)

# ============================================================
# GND splitter: Arduino GND (left @86) -> OLED GND / DS18B20 GND / KY-040 GND
# ============================================================
inpG,outG = splitter(GS_X,GS_Y,CG,"GND 1→3")
wire([(LPX,86),(LPX-5,86),(LPX-5,99.6),(135.5,99.6),(135.5,GS_Y),(inpG[0],inpG[1])],CG,2.4)
dot(LPX,86,CG)
yg=[117.85, 119.15, 120.45]
for (ox,oy),tx,yy in zip(outG,(o_gnd,d_gnd,k_gnd),yg):
    wire([(ox,oy),(ox,yy),(tx,yy),(tx,BOX_YB)],CG,2.0)
pin_label(o_gnd,BOX_YB,"GND",CG); pin_label(d_gnd,BOX_YB,"GND",CG); pin_label(k_gnd,BOX_YB,"GND",CG)

# ============================================================
# Title + subtitle + notes + legend
# ============================================================
ax.text(112,9.5,"2U Smart Rack Fan - Wiring Diagram",
        fontsize=16,fontweight="bold",ha="center",color="#222")
ax.text(112,5.6,'Two 1-to-3 splitters (one 5V, one GND) power the OLED, DS18B20 and KY-040; fans and signal lines plug straight into the Arduino.\n'
        'TACH uses the internal pull-up + DS18B20 module has an onboard 4.7k → no external resistors; 12V → onboard DC barrel jack → VIN.',
        fontsize=9.5,ha="center",va="top",color="#555",linespacing=1.5)

# Notes box (empty area right of the board: x>88 clears the D2/D9 lines, y 45-59 clears the fan 12V/GND corridor)
ax.text(89,59,'How to read: solid dot ● = junction (connected); lines crossing without a dot\n'
        'only overlap in the drawing and are NOT connected.\n'
        '"1→3" blocks = one-in/three-out dupont splitter heads (two: one 5V, one GND).\n'
        'Power/analog headers are on one side of the board, digital on the other; 5V/GND\n'
        'come from the power side. The fans get their own GND pin (@83), the modules use\n'
        'another (@86); 12V enters via the onboard DC barrel jack → VIN.',
        fontsize=8.5,ha="left",va="top",color="#444",
        bbox=dict(boxstyle="round,pad=0.6",fc="#fff8e1",ec="#d8c98a"),zorder=20)

# Legend (bottom left, below the Arduino)
legend=[("+12V → VIN",C12),("+5V (1→3 splitter)",C5),("GND (splitter / fans)",CG),
        ("PWM  D9 → 3 fans",CPWM),("TACH  D2 · master fan",CTAC),("1-Wire DQ  D4",CDQ),
        ("Encoder  D3/D6/D12",CENC),("OLED I2C  SDA/SCL",COLED)]
lx,ly=5,35
ax.add_patch(FancyBboxPatch((lx-3,ly-len(legend)*3.4+0.5),46,len(legend)*3.4+7.5,
             boxstyle="round,pad=0.3",fc="white",ec="#cfcfcf",lw=1.0,zorder=19))
ax.text(lx-1,ly+4,"Wire colors / pins",fontsize=10,fontweight="bold",ha="left",zorder=21)
for i,(lab,col) in enumerate(legend):
    yy=ly-i*3.4
    ax.plot([lx,lx+5],[yy,yy],color=col,lw=3,solid_capstyle="round",zorder=21)
    ax.text(lx+6.5,yy,lab,fontsize=9,va="center",ha="left",zorder=21)

import os
_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiring.png")
plt.savefig(_OUT, dpi=170, bbox_inches="tight", facecolor="white")
print("saved", _OUT)
