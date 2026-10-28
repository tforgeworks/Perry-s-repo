"""Build a clean, printable CAD model of Jack Beard's keymod handguard.

Every dimension below was measured on the aligned 3D scan (see measure notes in
README.md). Coordinates: X along the bore axis (rear lugs at X=0.25, muzzle end at
X=387.4), Z up toward the Picatinny rail, Y to the right when looking forward.
The bore axis is the X axis.

Usage: python build_handguard.py --out ../handguard_base.stl
"""
import argparse
import json
import os

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
SEG = 180  # circle segments

# ---------------------------------------------------------------- dimensions (mm)
R_OUT = 19.72         # tube outer radius (OD 39.44)
FLAT_SIDE = 18.15     # keymod side flats, distance from axis
FLAT_BOT = 18.55      # bottom keymod flat, distance from axis
PANEL_X = 63.0        # rear end of the flats (step into the rear tube)
X_FACE = 2.75         # rear face of tube, rail and clamp block
X_LUG = 0.25          # rear end of the two anti-rotation lugs
X_END = 387.4         # muzzle end
CHAMFER = 0.5

R_BORE_REAR = 17.30   # barrel-nut bore (ID 34.6, scan 34.4 + 0.2 print clearance)
X_BORE_REAR = 60.0    # depth of the barrel-nut bore
R_BORE = 16.30        # bore in front of the barrel nut (ID 32.6)
CHAN_W = 5.5          # half width of the channel under the rail
CHAN_TOP = 27.0       # channel ceiling

# Picatinny rail (MIL-STD-1913 profile, height from scan)
RAIL_TOP = 31.10
RAIL_TOP_HALF = 7.84  # 0.617 in top flat
RAIL_APEX_HALF = 10.6  # 0.835 in across the dovetail
RAIL_NECK_HALF = 8.12
RAIL_SLOT_W = 5.23    # 0.206 in
RAIL_SLOT_FLOOR = 28.5
RAIL_SLOT_X0 = 10.7   # first slot centre
RAIL_PITCH = 10.0     # 0.394 in
RAIL_SLOTS = 37

# Lightening slots and keymod rows: (template, x0, pitch, count, sides)
ROWS = [
    ("upper", 69.0, 18.83, 17, (1, -1)),
    ("lower", 68.75, 18.83, 17, (1, -1)),
    ("keymod", 78.45, 20.0, 15, (1, -1)),
    ("bottomkey", 86.95, 20.0, 14, (1,)),
]
CUT_DEG = {"upper": 60.0, "lower": None}  # milling direction of the slot walls
FRONT_HOLE_X = 377.2
FRONT_HOLE_D = 11.0

# Rear clamp block
KEEL_HALF = 8.2
KEEL_BOT = -29.07
BOSS_X = (16.2, 46.0)
BOSS_HALF = 11.8
BOSS_BOT = -27.3
WING_INNER = 4.9
SCREW_X = (23.3, 39.4)  # two cross bolts, axis along Y
SCREW_Z = -22.3
CENTER_SCREW_X = 31.3   # vertical screw on the bottom centre
CLEAR_D = 4.5           # M4 clearance
TAP_D = 3.4             # pilot for M4 / #8-32 threads (or drill out for an insert)
CBORE_D = 7.6
SLIT = (4.2, 5.6)       # Y range of the clamp slit
SLIT_X = 52.0

FIT_TEST_X = 70.0


def to_X(m):
    """Map a solid built along +Z (x->Y, y->Z, z->X) into handguard coordinates."""
    return m.transform(np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]], float))


def extrude_x(cs, x0, x1):
    return to_X(Manifold.extrude(cs, x1 - x0).translate((0, 0, x0)))


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl_x(r, x0, x1):
    return to_X(Manifold.cylinder(x1 - x0, r, r, SEG).translate((0, 0, x0)))


def cyl_y(r, x, z, y0, y1):
    c = Manifold.cylinder(y1 - y0, r, r, 64)  # along Z
    m = np.array([[1, 0, 0, x], [0, 0, 1, y0], [0, 1, 0, z]], float)  # z->Y, y->Z
    return c.transform(m)


def cyl_z(r, x, y, z0, z1):
    return Manifold.cylinder(z1 - z0, r, r, 64).translate((x, y, z0))


def outer_r(theta):
    """Distance from the axis to the outer surface of the slotted section along angle
    theta (0 = up toward the rail, +90 = +Y)."""
    s, c = np.sin(theta), np.cos(theta)
    r = np.full_like(theta, R_OUT)
    with np.errstate(divide="ignore"):
        r = np.minimum(r, np.where(np.abs(s) > 1e-9, FLAT_SIDE / np.abs(s), np.inf))
        r = np.minimum(r, np.where(c < -1e-9, FLAT_BOT / -c, np.inf))
        neck = RAIL_NECK_HALF / np.maximum(np.abs(s), 1e-9)
    in_neck = (neck * np.abs(c) > np.sqrt(R_OUT**2 - RAIL_NECK_HALF**2)) & (c > 0)
    return np.where(in_neck, neck, r)


def hole_cutter(outline, x_c, theta_c_deg, side, depth_in=11.0, depth_out=24.0, cut_deg=None):
    """Prism through the wall whose outline on the outer surface matches the scan.
    outline: (n,2) of (dx mm, dtheta deg) about the hole centroid."""
    th = np.radians(side * (theta_c_deg + outline[:, 1]))
    tc = np.radians(side * (theta_c_deg if cut_deg is None else cut_deg))
    r = outer_r(th)
    Y, Z = r * np.sin(th), r * np.cos(th)
    n = np.array([np.sin(tc), np.cos(tc)])
    t = np.array([np.cos(tc), -np.sin(tc)])
    u = outline[:, 0]
    v = Y * t[0] + Z * t[1]
    pts = np.c_[u, v]
    s_out = Y * n[0] + Z * n[1]
    if cut_deg is not None:
        depth_in, depth_out = s_out.min() - 1.0, s_out.max() + 3.0
    if side < 0:  # mirroring flips the winding
        pts = pts[::-1]
    cs = CrossSection([pts.tolist()])
    if cs.area() < 0:
        cs = CrossSection([pts[::-1].tolist()])
    prism = Manifold.extrude(cs, depth_out - depth_in).translate((0, 0, depth_in))
    # local x -> X, local y -> t, local z -> n
    m = np.array([[1, 0, 0, x_c],
                  [0, t[0], n[0], 0],
                  [0, t[1], n[1], 0]], float)
    return prism.transform(m)


def rail_profile():
    h = RAIL_APEX_HALF - RAIL_TOP_HALF  # 45 deg upper flank
    apex_z = RAIL_TOP - h
    neck_z = apex_z - (RAIL_APEX_HALF - RAIL_NECK_HALF)  # 45 deg lower flank
    right = [(RAIL_NECK_HALF, 12.0), (RAIL_NECK_HALF, neck_z), (RAIL_APEX_HALF, apex_z),
             (RAIL_TOP_HALF, RAIL_TOP)]
    left = [(-y, z) for y, z in reversed(right)]
    return CrossSection([right + left])


def build(templates):
    # --- outer body
    circle = CrossSection.circle(R_OUT, SEG)
    flats = CrossSection.square((2 * FLAT_SIDE, 2 * R_OUT + 2)).translate((-FLAT_SIDE, -FLAT_BOT))
    body = extrude_x(circle, X_FACE, X_END)
    outside_flats = CrossSection.square((4 * R_OUT, 4 * R_OUT)).translate((-2 * R_OUT, -2 * R_OUT)) - flats
    body -= extrude_x(outside_flats, PANEL_X, X_END + 1)
    rail = extrude_x(rail_profile(), X_FACE, X_END)
    for k in range(RAIL_SLOTS):
        xc = RAIL_SLOT_X0 + k * RAIL_PITCH
        rail -= box(xc - RAIL_SLOT_W / 2, xc + RAIL_SLOT_W / 2, -13, 13, RAIL_SLOT_FLOOR, 40)
    body += rail

    # --- rear clamp block (keel + cross-bolt boss)
    keel_side = CrossSection([[(X_FACE, -15.0), (X_FACE + 0.3, -20.5), (15.0, KEEL_BOT),
                               (47.5, KEEL_BOT), (59.0, -20.5), (59.0, -15.0)]])
    keel = Manifold.extrude(keel_side, 2 * KEEL_HALF).translate((0, 0, -KEEL_HALF))
    keel = keel.transform(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0]], float))  # (x,y,z)->(X,Z,Y)
    boss = box(BOSS_X[0], BOSS_X[1], -BOSS_HALF, BOSS_HALF, BOSS_BOT, -14.0)
    clamp = keel + boss
    for s in (1, -1):  # wings sit 1.8 mm above the centre keel
        y0, y1 = sorted((s * WING_INNER, s * 14.0))
        clamp -= box(BOSS_X[0] - 0.01, BOSS_X[1] + 0.01, y0, y1, -31, BOSS_BOT)
    # ramp from the front of the boss into the tube on the +Y side
    clamp += Manifold.batch_hull([box(45.9, 46.0, WING_INNER, BOSS_HALF, -23.5, -15.5),
                                  box(59.5, 59.6, WING_INNER, 8.5, -19.0, -18.6)])
    body += clamp

    # --- inside
    inner = cyl_x(R_BORE_REAR, -1, X_BORE_REAR) + cyl_x(R_BORE, X_BORE_REAR - 0.01, X_END + 1)
    inner += box(-1, X_END + 1, -CHAN_W, CHAN_W, 0, CHAN_TOP)
    body -= inner

    # --- end chamfers (outer edge of the tube, inner edge of the bore)
    for x, sgn in ((X_FACE, 1), (X_END, -1)):
        keep = Manifold.cylinder(CHAMFER * 2, R_OUT - CHAMFER, R_OUT + CHAMFER, SEG)
        ring_cut = Manifold.cylinder(CHAMFER * 2, R_OUT + 5, R_OUT + 5, SEG) - keep
        if sgn < 0:
            ring_cut = ring_cut.mirror((0, 0, 1)).translate((0, 0, CHAMFER * 2))
        ring_cut = to_X(ring_cut.translate((0, 0, x if sgn > 0 else x - CHAMFER * 2)))
        # leave the rail and the clamp block square
        ring_cut ^= (box(x - 3, x + 3, -30, 30, -18.0, 18.0)
                     - box(x - 3, x + 3, -RAIL_NECK_HALF - 0.5, RAIL_NECK_HALF + 0.5, 0, 40))
        body -= ring_cut
        bore_r = R_BORE_REAR if sgn > 0 else R_BORE
        cham = Manifold.cylinder(1.0, bore_r + 0.8, bore_r - 0.2, SEG)
        if sgn < 0:
            cham = cham.mirror((0, 0, 1)).translate((0, 0, 1.0))
        body -= to_X(cham.translate((0, 0, x - 0.01 if sgn > 0 else x - 0.99)))

    # --- anti-rotation lugs that sit against the upper receiver
    keep = (CrossSection.square((12, 12)).translate((8.3, 10.9))
            + CrossSection.square((12, 12)).translate((-20.3, 10.9)))
    lug_ring = CrossSection.circle(R_OUT - 0.01, SEG + 7) - CrossSection.circle(R_BORE_REAR + 0.01, SEG + 7)
    body += extrude_x(lug_ring ^ keep, X_LUG, X_FACE + 1.3)

    # --- slots and keymods
    cutters = []
    for name, x0, pitch, count, sides in ROWS:
        tpl = templates[name]
        outline = np.asarray(tpl["outline_dx_mm_dtheta_deg"])
        for k in range(count):
            for side in sides:
                cutters.append(hole_cutter(outline, x0 + k * pitch, tpl["theta_center_deg"], side,
                                           cut_deg=CUT_DEG.get(name)))
    ang = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    circ = np.c_[FRONT_HOLE_D / 2 * np.cos(ang), np.degrees(FRONT_HOLE_D / 2 * np.sin(ang) / FLAT_SIDE)]
    for side in (1, -1):
        cutters.append(hole_cutter(circ, FRONT_HOLE_X, 90.0, side))
    body -= Manifold.batch_boolean(cutters, _union_op())

    # --- clamp hardware holes and slit
    for x in SCREW_X:
        body -= cyl_y(CLEAR_D / 2, x, SCREW_Z, -20, SLIT[1])
        body -= cyl_y(TAP_D / 2, x, SCREW_Z, SLIT[0], 20)
        body -= cyl_y(CBORE_D / 2, x, SCREW_Z, -20, -BOSS_HALF + 2.0)
    body -= cyl_z(CLEAR_D / 2, CENTER_SCREW_X, 0, -35, -10)
    body -= cyl_z(CBORE_D / 2, CENTER_SCREW_X, 0, -35, KEEL_BOT + 4.2)
    body -= box(-1, SLIT_X, SLIT[0], SLIT[1], -35, -12)
    body -= cyl_z(1.6, SLIT_X, (SLIT[0] + SLIT[1]) / 2, -35, -12)
    return body


def _union_op():
    from manifold3d import OpType
    return OpType.Add


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "handguard_base.stl"))
    ap.add_argument("--templates", default=os.path.join(HERE, "..", "data", "hole_templates.json"))
    ap.add_argument("--fit-test", default=None, help="also write the rear 70 mm as a quick fit-test print")
    a = ap.parse_args()
    templates = json.load(open(a.templates))
    body = build(templates)
    tm = to_trimesh(body)
    print("watertight", tm.is_watertight, "volume cm3", round(tm.volume / 1000, 1), "bounds", tm.bounds.round(2).tolist())
    tm.export(a.out)
    if a.fit_test:
        # rear 70 mm: barrel-nut bore, lugs, clamp and the start of the rail, for a quick test print
        test = to_trimesh(body.trim_by_plane((-1, 0, 0), -FIT_TEST_X))
        print("fit test watertight", test.is_watertight, "bounds", test.bounds.round(2).tolist())
        test.export(a.fit_test)


if __name__ == "__main__":
    main()
