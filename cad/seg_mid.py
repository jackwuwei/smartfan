# Middle segment (fan 2) -- standalone printed part (Bambu P1S)
from rack_fan_2u import make_segment, SEAM1, SEAM2


def gen_step():
    s = make_segment(SEAM1, SEAM2, [(SEAM1, "R"), (SEAM2, "L")])
    s.label = "seg_mid"
    return s
