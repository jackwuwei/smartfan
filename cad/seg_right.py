# Right segment (fan 1 (master) + control area: OLED window / knob / Arduino posts / DS18B20 cradle + right rack ear) -- standalone printed part (Bambu P1S)
from rack_fan_2u import make_segment, SEAM2, PANEL_W


def gen_step():
    s = make_segment(SEAM2, PANEL_W / 2, [(SEAM2, "R")])
    s.label = "seg_right"
    return s
