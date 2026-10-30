"""Black-and-white figures for the printed assembly manual (manual/fig_*.png).

Reuses the assembly guide's renderer with a grey palette: the handguard light grey, the rear
snake piece mid grey, the head piece darker, hardware black.
"""
import os

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

import assembly_guide as AG
import build_handguard as HG

ROOT = AG.ROOT
OUT = os.path.join(ROOT, "manual")
LIGHT, MID, DARKER, BLACK = (np.array([v, v, v]) for v in (0.86, 0.66, 0.50, 0.12))
AG.BG = (255, 255, 255)
FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", 34)


def label(d, sc, p, text, off):
    q = sc.px(p)[0]; t = q + np.array(off)
    d.line([tuple(t), tuple(q)], fill=(0, 0, 0), width=3)
    anchor = "md" if off[1] < 0 else "ma"
    box = d.textbbox(tuple(t), text, font=FONT, anchor=anchor)
    d.rectangle([box[0] - 8, box[1] - 6, box[2] + 8, box[3] + 6], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    d.text(tuple(t), text, fill=(0, 0, 0), font=FONT, anchor=anchor)


def save(img, name):
    img = AG.autocrop(img).convert("L")
    img.save(os.path.join(OUT, name))
    print(name, img.size)


def main():
    os.makedirs(OUT, exist_ok=True)
    base = trimesh.load(os.path.join(ROOT, "handguard_base.stl"))
    rear = trimesh.load(os.path.join(ROOT, "snake_rear.3mf"), force="mesh")
    front = trimesh.load(os.path.join(ROOT, "snake_front.3mf"), force="mesh")
    L = AG.LOCK
    view = np.array([0.0, -0.86, -0.51])

    # 1. the parts, laid out
    sc = AG.Scene(view, AG.UP, np.array([-10.0, -60, -130]), np.array([520.0, 60, 70]), res=0.45)
    img = sc.render([(base, LIGHT), (AG.moved_z(rear, -100), MID), (AG.moved_z(AG.moved(front, 50), -100), DARKER)])
    d = ImageDraw.Draw(img)
    label(d, sc, [200, 0, 40], "A  handguard", (0, -40))
    label(d, sc, [120, -30, -135], "B  snake rear piece", (0, 60))
    label(d, sc, [390, -30, -135], "C  snake head piece", (0, 60))
    save(img, "fig_parts.png")

    # 2. heat-set insert (rear piece, left bolt)
    rb = L["bolts"]["rear"][0]; BX = rb["x"]; BY = rb["insert_top_y"]; BS = rb["surface_y"]
    sci = AG.Scene([0.30, -0.90, -0.32], AG.UP, np.array([BX - 55, BY - 20, -45]), np.array([BX + 55, BS + 25, 45]), res=0.1)
    r_near = rear.slice_plane([BX - 45, 0, 0], [1, 0, 0]).slice_plane([BX + 45, 0, 0], [-1, 0, 0])
    img = sci.render([(r_near, MID), (AG.cyl_y(3.5, BS + 6, BS + 12, BX, 0.0), BLACK)], density=3.0)
    d = ImageDraw.Draw(img)
    label(d, sci, [BX, BS + 9, 3.5], "M5 heat-set insert", (260, -160))
    label(d, sci, [BX, BS, -5.5], "insert hole (one on each side of each piece)", (0, 260))
    save(img, "fig_insert.png")

    # 3. clamp from below
    scc = AG.Scene([0.15, 0.55, 0.82], AG.UP, np.array([-5.0, -32, -36]), np.array([75.0, 32, 30]), res=0.07)
    img = scc.render([(base.slice_plane([80, 0, 0], [-1, 0, 0]), LIGHT), (AG.clamp_screws(), BLACK)], density=3.0)
    d = ImageDraw.Draw(img)
    label(d, scc, [HG.SCREW_X[1], -HG.BOSS_HALF, HG.SCREW_Z], "2 x M4 x 25 bolts (nuts on the other side)", (260, 120))
    label(d, scc, [HG.CENTER_SCREW_X, 0, HG.KEEL_BOT], "centre screw", (-200, 80))
    save(img, "fig_clamp.png")

    # 4. the joint, pulled apart, tabs dark
    XJ = L["joint_x"]; W, H, TL = L["tab_size_mm"]
    tabs = []
    for t in L["tabs"]:
        b = trimesh.creation.box(extents=[TL + 6.0, W, H])
        b.apply_translation([t["face_x"] - TL / 2 + 3.0, 0, 0])
        b.apply_transform(trimesh.transformations.rotation_matrix(np.radians(t["theta"]), [-1, 0, 0]))
        b.apply_translation([0, t["y"], t["z"]])
        tabs.append(b)
    gap = 30.0
    scj = AG.Scene([0.30, -0.88, -0.36], AG.UP, np.array([XJ - 70, -50, -50]), np.array([XJ + 70 + gap, 50, 50]), res=0.1)
    img = scj.render([(rear.slice_plane([XJ - 50, 0, 0], [1, 0, 0]), MID),
                      (AG.moved(front.slice_plane([XJ + 60, 0, 0], [-1, 0, 0]), gap), DARKER),
                      (AG.moved(trimesh.util.concatenate(tabs), gap), BLACK)], density=3.0)
    save(img, "fig_joint.png")

    # 5. across the head piece's bolts, from the muzzle
    fb = L["bolts"]["front"][0]; FX = fb["x"]
    scb = AG.Scene([-1, 0, 0], AG.UP, np.array([FX, -62, -40]), np.array([FX, 62, 45]), res=0.06)
    cutx = lambda m: m.slice_plane([FX, 0, 0], [-1, 0, 0], cap=True).slice_plane([FX - 12, 0, 0], [1, 0, 0], cap=True)
    hw = []
    for b in L["bolts"]["front"]:
        s = 1 if b["side"] == "left" else -1
        y_f = abs(b["insert_top_y"]); Ls = float(b["screw"].split("x")[1].split()[0])
        lo, hi = (y_f - Ls, y_f) if s > 0 else (-y_f, -(y_f - Ls))
        hlo, hhi = (y_f, y_f + 5) if s > 0 else (-(y_f + 5), -y_f)
        hw += [AG.cyl_y(2.5, lo, hi, FX, 0.0), AG.cyl_y(4.25, hlo, hhi, FX, 0.0)]
    img = scb.render([(cutx(base), LIGHT), (cutx(front), DARKER), (trimesh.util.concatenate(hw), BLACK),
                      (AG.cyl_x(9.5, FX - 30, FX + 30), MID)], density=3.0)
    d = ImageDraw.Draw(img)
    label(d, scb, [FX, -abs(fb["insert_top_y"]) + 3, 0], "bolt tip in the keymod hole", (-40, 170))
    label(d, scb, [FX, 0, 0], "barrel", (0, 120))
    save(img, "fig_bolt_section.png")

    # 6. assembled, rifle's left side, with the bolt positions marked
    sca = AG.Scene([0, -1, 0], AG.UP, np.array([-5.0, -50, -50]), np.array([470.0, 50, 60]), res=0.3)
    asm = trimesh.util.concatenate([base, rear, front])
    img = sca.render([(base, LIGHT), (rear, MID), (front, DARKER)])
    d = ImageDraw.Draw(img)
    for p in ("rear", "front"):
        b = [q for q in L["bolts"][p] if q["side"] == "left"][0]
        label(d, sca, [b["x"], b["surface_y"], 0], f"{p} bolt", (0, -170))
    save(img, "fig_assembled.png")
    del asm


if __name__ == "__main__":
    main()
