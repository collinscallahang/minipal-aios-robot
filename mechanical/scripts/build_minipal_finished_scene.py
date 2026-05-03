"""Generate the final MiniPal SolidWorks scene.

This creates one self-contained SLDPRT that matches the requested submission
style: transparent case, visible internal modules, and exploded reference
modules around the robot like the SolidWorks screenshot.
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


def case_shell(model):
    # Main transparent box, matching the screenshot's see-through case.
    box(model, "transparent top panel", (0, 34, 0), (100, 3, 90), COL["glass"])
    box(model, "transparent bottom panel", (0, -34, 0), (100, 3, 90), COL["glass"])
    box(model, "transparent left wall", (-50, 0, 0), (3, 70, 90), COL["glass"])
    box(model, "transparent right wall", (50, 0, 0), (3, 70, 90), COL["glass"])
    box(model, "transparent front wall", (0, 0, -45), (100, 70, 3), COL["glass"])
    box(model, "transparent rear wall", (0, 0, 45), (100, 70, 3), COL["glass"])
    for x in (-51.8, 51.8):
        box(model, "dark vertical case edge", (x, 0, -46.8), (2.4, 72, 2.4), COL["edge"])
        box(model, "dark rear vertical case edge", (x, 0, 46.8), (2.4, 72, 2.4), COL["edge"])
    for y in (-36, 36):
        box(model, "dark horizontal case edge", (0, y, -46.8), (104, 2.4, 2.4), COL["edge"])
        box(model, "dark rear horizontal case edge", (0, y, 46.8), (104, 2.4, 2.4), COL["edge"])


def internal_modules(model):
    box(model, "internal 5V power bank / battery", (14, -20, -7), (62, 12, 42), COL["battery"])
    box(model, "internal ESP32 controller board", (8, -2, -16), (58, 3, 30), COL["esp"])
    box(model, "ESP32 module shield", (8, 4, -17), (24, 8, 18), COL["dark"])
    box(model, "inside servo block", (15, 15, -8), (23, 32, 14), COL["servo"])
    cyl_z(model, "inside servo rotating hub", (15, 15, -20), 18, 4, COL["horn"])
    box(model, "inside servo horn bar", (15, 31, -20), (62, 5, 3), COL["horn"])
    box(model, "front HC-SR04 sensor board installed", (-25, -3, -49), (45, 20, 2.5), COL["board"])
    cyl_y(model, "installed left ultrasonic eye", (-37, -3, -54), 16, 8, COL["eye"])
    cyl_y(model, "installed right ultrasonic eye", (-13, -3, -54), 16, 8, COL["eye"])
    box(model, "top wake button module installed", (18, 39, -6), (52, 8, 5), COL["trim"])
    cyl_z(model, "status LED ring on body", (-24, -1, -50), 14, 3, COL["led"])
    box(model, "speaker slot", (12, -8, -50.5), (38, 4, 2), COL["dark"])
    box(model, "wire harness inside", (-5, 20, -25), (65, 3, 3), COL["wire"])
    box(model, "vertical wire harness", (-32, 8, -24), (3, 36, 3), COL["wire"])


def exploded_parts(model):
    # Left side: controller, sensor and small modules exploded around the case.
    box(model, "exploded ESP32 board reference", (-125, -8, -12), (55, 28, 3), COL["esp"])
    box(model, "exploded ESP32 USB connector", (-94, -8, -12), (8, 10, 6), COL["dark"])
    box(model, "exploded ESP32 pin row upper", (-125, 8, -12), (56, 3, 3), COL["pin"])
    box(model, "exploded ESP32 pin row lower", (-125, -24, -12), (56, 3, 3), COL["pin"])

    box(model, "exploded HC-SR04 board reference", (-115, -42, -22), (45, 20, 2.5), COL["board"])
    cyl_y(model, "exploded HC-SR04 left eye", (-127, -42, -29), 16, 8, COL["eye"])
    cyl_y(model, "exploded HC-SR04 right eye", (-103, -42, -29), 16, 8, COL["eye"])

    box(model, "exploded WS2812 LED board", (-160, -20, -5), (12, 12, 2), COL["dark"])
    cyl_z(model, "exploded WS2812 diffuser", (-160, -20, -8), 8, 3, COL["led"])
    cyl_z(model, "exploded buzzer module", (-142, 14, -8), 12, 9, COL["dark"])
    box(model, "exploded button body", (-165, 23, -5), (10, 16, 8), COL["red"])

    # Top/right side: cover panels, feet and servo group, like the screenshot.
    for i, x in enumerate((-38, 0, 38), start=1):
        cyl_z(model, f"exploded rubber foot {i}", (x, 72, 4), 13, 5, COL["edge"])
    box(model, "exploded top lid long panel", (16, 65, -2), (86, 3, 88), COL["glass"])
    box(model, "exploded front trim strip", (20, 54, -50), (72, 8, 4), COL["trim"])
    box(model, "exploded rear cover strip", (12, 58, 42), (78, 4, 4), COL["glass"])

    box(model, "exploded SG90 servo body", (112, 30, -5), (23, 32, 14), COL["servo"])
    box(model, "exploded servo mounting ear upper", (112, 49, -5), (42, 5, 14), COL["servo"])
    box(model, "exploded servo mounting ear lower", (112, 11, -5), (42, 5, 14), COL["servo"])
    cyl_z(model, "exploded servo hub", (112, 30, -18), 18, 5, COL["horn"])
    box(model, "exploded servo horn", (112, 59, -18), (64, 4, 3), COL["horn"])
    box(model, "exploded servo cable", (83, 22, -16), (3, 44, 3), COL["wire"])

    box(model, "right side dimension marker 70mm", (150, 0, -45), (2, 70, 2), COL["edge"])
    box(model, "bottom dimension marker 100mm", (0, -57, -45), (100, 2, 2), COL["edge"])


def save_all(model):
    FINISHED.parent.mkdir(parents=True, exist_ok=True)
    model.ShowNamedView2("*Isometric", 7)
    model.ViewZoomtofit2()
    model.SaveAs3(str(FINISHED), 0, 1)
    model.SaveAs3(str(STEP), 0, 1)
    model.SaveAs3(str(PNG), 0, 1)


def main() -> int:
    sw = sw_app()
    try:
        sw.CloseDoc("MiniPal_finished_robot.SLDPRT")
    except Exception:
        pass
    model = new_part(sw)
    case_shell(model)
    internal_modules(model)
    exploded_parts(model)
    save_all(model)
    print(f"created {FINISHED}")
    print(f"created {STEP}")
    print(f"created {PNG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
