# Left segment (fan 3 + left rack ear) -- standalone printed part (Bambu P1S)
from rack_fan_2u import make_segment, SEAM1, PANEL_W


def gen_step():
    s = make_segment(-PANEL_W / 2, SEAM1, [(SEAM1, "L")])
    s.label = "seg_left"
    return s
