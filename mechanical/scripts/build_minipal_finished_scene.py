"""Generate the final assembled MiniPal SolidWorks robot.

This creates one self-contained SLDPRT for submission. The output is an
integrated product model that follows the browser simulator robot silhouette
instead of the earlier exploded/reference layout.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pythoncom
import win32com.client
from win32com.client import VARIANT


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "mechanical" / "solidworks_minipal"
FINISHED = OUT_DIR / "finished" / "MiniPal_finished_robot.SLDPRT"
STEP = OUT_DIR / "finished" / "MiniPal_finished_robot.step"
PNG = OUT_DIR / "finished" / "MiniPal_finished_robot_preview.png"

MM = 0.001
FRONT_PLANE = "\u524d\u89c6\u57fa\u51c6\u9762"
TOP_PLANE = "\u4e0a\u89c6\u57fa\u51c6\u9762"


@dataclass(frozen=True)
class Color:
    r: float
    g: float
    b: float
    ambient: float = 0.45
    diffuse: float = 0.85
    specular: float = 0.22
    shininess: float = 0.25
    transparency: float = 0.0
    emission: float = 0.0

    def variant(self) -> VARIANT:
        return VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8,
            [
                self.r,
                self.g,
                self.b,
                self.ambient,
                self.diffuse,
                self.specular,
                self.shininess,
                self.transparency,
                self.emission,
            ],
        )


COL = {
    "glass": Color(0.72, 0.86, 0.92, transparency=0.55),
    "edge": Color(0.18, 0.22, 0.28, transparency=0.15),
    "board": Color(0.08, 0.47, 0.38),
    "esp": Color(0.08, 0.36, 0.72),
    "dark": Color(0.04, 0.05, 0.07),
    "pin": Color(0.88, 0.68, 0.20),
    "battery": Color(0.55, 0.28, 0.12),
    "servo": Color(0.92, 0.92, 0.88),
    "horn": Color(0.95, 0.95, 0.90),
    "eye": Color(0.88, 0.90, 0.90, specular=0.55, shininess=0.5),
    "trim": Color(0.82, 0.46, 0.18),
    "led": Color(0.08, 0.34, 0.72, specular=0.55, shininess=0.45),
    "red": Color(0.88, 0.16, 0.12),
    "wire": Color(0.03, 0.03, 0.04),
    "sim_body": Color(0.93, 0.96, 0.98),
    "sim_head": Color(0.96, 0.98, 1.0),
    "sim_shadow": Color(0.58, 0.66, 0.74),
    "sim_window": Color(0.72, 0.83, 0.91, transparency=0.10),
    "sim_eye_blue": Color(0.05, 0.28, 0.52, specular=0.45, shininess=0.45),
    "sim_eye_ring": Color(0.76, 0.82, 0.88),
    "sim_led_blue": Color(0.04, 0.36, 0.70, specular=0.5, shininess=0.45),
}


def m(v: float) -> float:
    return v * MM


def sw_app():
    sw = win32com.client.Dispatch("SldWorks.Application")
    sw.Visible = True
    return sw


def new_part(sw):
    tmpl = sw.GetUserPreferenceStringValue(8)
    doc = sw.NewDocument(tmpl, 0, 0, 0)
    return doc if doc is not None else sw.ActiveDoc


def select_plane(model, name: str):
    model.ClearSelection2(True)
    if not model.SelectByID(name, "PLANE", 0, 0, 0):
        raise RuntimeError(f"cannot select plane {name}")


def extrude(model, depth_mm: float, start_mm: float = 0.0, merge: bool = False):
    return model.FeatureManager.FeatureExtrusion2(
        True,
        False,
        False,
        0,
        0,
        m(depth_mm),
        0,
        False,
        False,
        False,
        False,
        0,
        0,
        False,
        False,
        False,
        False,
        merge,
        True,
        True,
        3 if abs(start_mm) > 1e-9 else 0,
        m(start_mm),
        False,
    )


def paint(feat, color: Color):
    feat.SetMaterialPropertyValues2(color.variant(), 1, "")


def box(model, name: str, c: tuple[float, float, float], s: tuple[float, float, float], color: Color):
    x, y, z = c
    sx, sy, sz = s
    select_plane(model, FRONT_PLANE)
    sk = model.SketchManager
    sk.InsertSketch(True)
    sk.CreateCenterRectangle(m(x), m(y), 0, m(x + sx / 2), m(y + sy / 2), 0)
    sk.InsertSketch(True)
    feat = extrude(model, sz, z - sz / 2, False)
    feat.Name = name
    paint(feat, color)
    return feat


def cyl_z(model, name: str, c: tuple[float, float, float], d: float, h: float, color: Color):
    x, y, z = c
    select_plane(model, FRONT_PLANE)
    sk = model.SketchManager
    sk.InsertSketch(True)
    model.CreateCircleByRadius2(m(x), m(y), 0, m(d / 2))
    sk.InsertSketch(True)
    feat = extrude(model, h, z - h / 2, False)
    feat.Name = name
    paint(feat, color)
    return feat


def cyl_y(model, name: str, c: tuple[float, float, float], d: float, h: float, color: Color):
    x, y, z = c
    select_plane(model, TOP_PLANE)
    sk = model.SketchManager
    sk.InsertSketch(True)
    model.CreateCircleByRadius2(m(x), 0, m(z), m(d / 2))
    sk.InsertSketch(True)
    feat = extrude(model, h, y - h / 2, False)
    feat.Name = name
    paint(feat, color)
    return feat


def assembled_body(model):
    # Product shell is kept as an integrated robot body, matching simulation/index.html.
    box(model, "assembled robot body envelope", (0, 36, 0), (104, 92, 56), COL["sim_body"])
    box(model, "body lower inset shadow", (10, 6, -30), (74, 14, 3), COL["sim_shadow"])
    box(model, "body right side inset shadow", (42, 36, -30), (12, 78, 3), COL["sim_shadow"])
    box(model, "body left edge seam", (-52, 36, -30), (3, 90, 3), COL["edge"])
    box(model, "body right edge seam", (52, 36, -30), (3, 90, 3), COL["edge"])
    box(model, "body top edge seam", (0, 82, -30), (104, 3, 3), COL["edge"])
    box(model, "body bottom edge seam", (0, -10, -30), (104, 3, 3), COL["edge"])

    cyl_z(model, "front LED status ring outer", (0, 60, -31.5), 28, 3.6, COL["sim_led_blue"])
    cyl_z(model, "front LED status ring center", (0, 60, -33.2), 15, 3.8, COL["sim_body"])

    box(model, "front ESP32 display window", (0, 30, -32), (70, 30, 3), COL["sim_window"])
    box(model, "display text block ESP32", (-18, 34, -34), (24, 4, 1.4), COL["dark"])
    box(model, "display text block STATE", (18, 24, -34), (30, 4, 1.4), COL["dark"])

    for i, x in enumerate((-26, -16, -6, 4, 14, 24), start=1):
        box(model, f"speaker grille integrated slot {i}", (x, 0, -33), (5, 3, 2), COL["dark"])

    box(model, "internal 5V power pack seated in body", (18, 12, 8), (62, 12, 38), COL["battery"])
    box(model, "internal ESP32 controller board seated", (0, 28, -2), (56, 3, 28), COL["esp"])
    box(model, "internal wire harness routed", (-18, 45, -12), (3, 44, 3), COL["wire"])
    box(model, "USB port side opening", (53, 30, -10), (3, 14, 9), COL["dark"])


def assembled_head_and_motion(model):
    box(model, "neck block with SG90 servo installed", (0, 91, 0), (30, 20, 36), COL["sim_shadow"])
    box(model, "SG90 servo body inside neck", (0, 91, -6), (23, 18, 24), COL["servo"])
    cyl_z(model, "SG90 servo hub under head", (0, 102, -27), 18, 4, COL["horn"])
    box(model, "servo horn locked into head", (0, 109, -27), (56, 4, 3), COL["horn"])

    box(model, "assembled head shell", (0, 130, 0), (86, 60, 44), COL["sim_head"])
    box(model, "head lower face slot", (0, 111, -33), (40, 5, 3), COL["dark"])
    box(model, "head right side shadow", (37, 130, -25), (8, 50, 3), COL["sim_shadow"])
    box(model, "head bottom shadow", (0, 101, -25), (74, 7, 3), COL["sim_shadow"])

    box(model, "HC-SR04 board installed behind face", (0, 132, -34), (58, 20, 2), COL["board"])
    for side, x in (("left", -22), ("right", 22)):
        cyl_z(model, f"{side} ultrasonic eye dark ring", (x, 134, -37), 23, 3.5, COL["dark"])
        cyl_z(model, f"{side} ultrasonic eye silver ring", (x, 134, -39), 17, 3.5, COL["sim_eye_ring"])
        cyl_z(model, f"{side} ultrasonic eye blue center", (x, 134, -41), 11, 3, COL["sim_eye_blue"])
        cyl_z(model, f"{side} ultrasonic eye highlight", (x - 3, 138, -42.5), 3.2, 1.2, COL["sim_head"])

    cyl_y(model, "top wake button installed", (0, 163, 0), 16, 8, COL["red"])
    box(model, "top button mounting plate", (0, 158, 0), (30, 3, 20), COL["trim"])


def assembled_base_details(model):
    box(model, "front trim strip installed", (0, 84, -33), (82, 5, 4), COL["trim"])
    box(model, "rear translucent service panel", (0, 38, 30), (82, 50, 3), COL["glass"])
    box(model, "left foot installed", (-34, -18, -8), (22, 10, 18), COL["edge"])
    box(model, "right foot installed", (34, -18, -8), (22, 10, 18), COL["edge"])
    box(model, "rear stabilizer foot", (0, -18, 20), (58, 8, 12), COL["edge"])
    cyl_z(model, "WS2812 LED module mounted behind ring", (0, 60, -26), 12, 4, COL["led"])
    cyl_z(model, "buzzer installed behind speaker grille", (25, 0, -20), 14, 8, COL["dark"])
    box(model, "assembled robot footprint shadow", (0, -24, 0), (124, 3, 78), COL["sim_shadow"])


def assembled_robot(model):
    assembled_body(model)
    assembled_head_and_motion(model)
    assembled_base_details(model)


def save_all(model):
    FINISHED.parent.mkdir(parents=True, exist_ok=True)
    model.ShowNamedView2("*Isometric", 7)
    model.ViewZoomtofit2()
    model.SaveAs3(str(FINISHED), 0, 1)
    model.SaveAs3(str(STEP), 0, 1)
    model.ShowNamedView2("*Back", 2)
    model.ViewZoomtofit2()
    model.SaveAs3(str(PNG), 0, 1)


def main() -> int:
    sw = sw_app()
    try:
        sw.CloseDoc("MiniPal_finished_robot.SLDPRT")
    except Exception:
        pass
    model = new_part(sw)
    assembled_robot(model)
    save_all(model)
    print(f"created {FINISHED}")
    print(f"created {STEP}")
    print(f"created {PNG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
