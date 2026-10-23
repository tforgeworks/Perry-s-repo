"""Build a printable model of the chrome bar knob (mold mark 1439/A) from dimensions
measured on its 3D scan.

The knob is a drafted cup (skirt) with a hollow grip bar on the front and a shaft
sleeve in the middle. Every dimension below was measured on the aligned scan (see
README.md).

The model is a signed distance field (negative inside) made of exact primitives
(drafted cones, drafted slabs, planes, cylinders, boxes). They are combined with
rounded booleans, which give true circular fillets and edge rounds of a chosen radius
where two faces meet. The field is sampled on a fine grid, meshed with marching
cubes and decimated.

Model frame (mm): z is the knob axis, +z toward the back (the appliance panel),
the bar runs along x, the red pointer is at +x. The output STLs are translated so
the bar's front face sits at z=0 (print orientation: front face down).

Usage: python build_knob.py --outdir . [--res 0.08] [--scan-frame]
Writes knob.stl (assembled knob), knob_body.stl and knob_pointer.stl (print set: the
body prints face down, the pointer prints on its side and glues on), knob.build.json.
"""
import argparse
import json
import time
from pathlib import Path

import fast_simplification
import numpy as np
import trimesh
from scipy.interpolate import CubicSpline
from skimage import measure

T0 = time.time()

# ------------------------------------------------------------- measured dimensions
# heights along the axis
Z_FRONT = -29.50   # front face of the grip bar
Z_DISC = -10.40    # front face of the round disc beside the bar
Z_FLOOR = -7.72    # floor inside the cup
Z_RIM = 9.70       # back rim of the skirt
Z_PB = -26.75      # bottom of the two bar pockets
Z_BORE = -26.85    # bottom of the shaft bore
Z_TUBE = 20.45     # back end of the shaft sleeve

# skirt wall profiles (z, r) measured on the scan: ~5 deg draft below z=3.5, curving
# into a straight band from z~5.5 up to the rim; extrapolated linearly at both ends
SKIRT_OUT = [(-7.5, 27.572), (-5.0, 27.793), (-2.5, 28.026), (0.0, 28.252), (2.0, 28.426),
             (3.0, 28.503), (4.0, 28.569), (5.0, 28.609), (6.0, 28.632), (7.0, 28.641), (8.0, 28.643)]
SKIRT_IN = [(-6.0, 25.071), (-4.0, 25.283), (-2.0, 25.469), (0.0, 25.654), (2.0, 25.839),
            (3.0, 25.930), (4.0, 26.013), (5.0, 26.056), (6.0, 26.069), (7.0, 26.084), (8.0, 26.105)]
SKIRT_SLOPES = {"out": (0.0884, 0.0), "in": (0.095, 0.016)}   # dr/dz below and above the tables

# ends of the grip bar and of its pockets: arcs in plan whose curvature changes with height,
# nearly flat at the bar's front and as round as the skirt at the disc;
# x(y) = X0 + KX*(z+10.5) - (C0 + KC*(z+10.5)) * y^2/2
BAR_END = dict(X0=27.32, KX=0.0902, C0=0.0372, KC=0.00165)
POCKET_END = dict(X0=24.65, KX=0.100, C0=0.0408, KC=0.0022)

# grip bar and its pockets: half-widths with ~5.2 deg draft
W_BAR, K_BAR = 10.58, 0.0906      # bar outer half-width at z=-27.5, and its slope
W_PKT, K_PKT = 8.17, 0.0956       # pocket half-width at z=-24.5
X_PKT, K_PKT_END = 7.50, -0.058   # |x| of the pocket end next to the sleeve, at z=-24.5

# shaft sleeve
R_TUBE = 9.0
BORE_R, BORE_K, BORE_Z_STRAIGHT = 7.0, 0.02074, 3.0   # radius 7.0 at z=-24, draft up to z=3

# pointer block at the +x end of the right pocket (x-z steps, |y| <= half-width)
BLOCK_LOW = dict(x0=15.5, top=-23.2, half_w=4.05)     # lower step
BLOCK_HIGH = dict(x0=20.5, top=-6.1, half_w=4.05)     # tall block, 1.6 mm above the floor
BLOCK_TIP = dict(x0=22.7, top=-4.7, half_w=1.25)      # narrow tip against the skirt wall
# features of the original red insert's prongs, seen inside the pointer block (x, z profiles)
WEDGE = dict(pts=[(17.1, -23.3), (18.65, -21.35), (19.65, -21.35), (19.65, -23.3)], y=(-1.05, 0.9))
PAD = dict(pts=[(20.6, -10.2), (20.15, -10.2), (20.15, -7.9), (20.6, -7.9)], y=(-0.225, 0.225))  # flat, on the tall block's face
SLOT = dict(x=(21.6, 22.7), y=(-0.4, 0.7), bottom=-7.0)   # recess in the tall block's top, up to the tip's face
# rib along the bottom of the left pocket (sharp edged, no fillets, as on the original)
RIB = dict(x1=-8.5, top=-21.8, half_w=1.6, draft=0.1)   # half-width 1.6 at the top, widening downward
# round boss at the rib's wall end, centred on the rib and just touching the pocket's end
# wall; its top slopes down from its high edge toward the skirt
RIB_END = dict(x=-21.7, y=0.0, r=1.9, z_hi=-20.95, x_hi=-20.0, slope=0.33)
# dip in the rib's top next to the boss, centred on the rib: in section a gentle ramp down
# from the boss side, a flat bottom and a steeper rise; in plan a trapezoid, 2.0 mm wide at
# the boss end narrowing to 1.3 mm at the far end
RIB_DIP = dict(pts=[(-19.3, -21.5), (-19.0, -21.8), (-18.0, -22.3), (-17.2, -22.3), (-16.7, -21.8), (-16.4, -21.5)],
               half_w=(1.0, 0.65), x=(-19.0, -16.7))

# red pointer: raised L-shaped strip on the bar's +x end face and front face
PTR_HALF_W = 1.6
PTR_PROUD = 1.0      # how far it stands off the bar's front face
PTR_END_T = (1.07, 0.0145)  # thickness on the end face: 1.07 at z=-10, growing 0.0145 per mm toward the front
PTR_TOP = -8.4       # where it ends on the end face
PTR_FRONT_X = 19.0   # where it ends on the front face (7.1 mm from the bar's end)
PTR_BEND = 1.0       # outer radius of the bend over the bar's corner
# locating pins on the pointer (and matching holes in the body), square section
PIN, PIN_LEN, PIN_CLEAR = 1.2, 2.0, 0.1
PIN_FRONT_X = 23.0
PIN_END_Z = -19.0

# rounds (convex edges) and fillets (concave edges), radius in mm
R_RIM_OUT = 0.65      # back rim, outer edge
R_RIM_IN = 0.6        # back rim, inner edge
R_OUTER_EDGE = 0.8    # skirt and bar ends to the front faces, bar sides to bar ends
R_BAR_FRONT = 0.8     # bar sides to the bar front face
R_BAR_DISC = 1.0      # fillet, bar sides to the disc front face
R_FLOOR = 0.4         # fillet, cup floor to skirt wall
R_POCKET = 1.5        # pocket bottoms
R_POCKET_CORNER = 2.5 # pocket corners next to the sleeve
R_POCKET_END = 1.0    # pocket corners at the skirt end
R_POCKET_MOUTH = 0.5  # pocket opening in the cup floor
R_TUBE_BASE = 1.0     # fillet, sleeve to cup floor
R_TUBE_POCKET = 2.0   # fillet, sleeve to the pocket bottoms (1.0 up its sides, like at the floor)
R_TUBE_TOP = 0.4      # sleeve end, both edges
R_BORE_BOTTOM = 0.5
R_BLOCK = 0.6         # block edges
R_BLOCK_BASE = 0.8    # fillet, blocks to the pocket faces and skirt wall
R_PTR_EDGE = 0.3


def log(msg):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------- SDF operators
# Rounded booleans after hg_sdf (Mercury): exact circular blends for perpendicular faces.

def u_round(a, b, r):
    """Union with a fillet of radius r."""
    return np.maximum(r, np.minimum(a, b)) - np.hypot(np.maximum(r - a, 0), np.maximum(r - b, 0))


def i_round(a, b, r):
    """Intersection with the edge rounded to radius r."""
    return np.minimum(-r, np.maximum(a, b)) + np.hypot(np.maximum(r + a, 0), np.maximum(r + b, 0))


def d_round(a, b, r):
    """Difference a - b with the new edges rounded to radius r."""
    return i_round(a, -b, r)


def drafted(v, w, k):
    """Distance to the plane v = w(z) for a slope dw/dz = k (v measured perpendicular to z)."""
    return (v - w) / np.sqrt(1 + k * k)


def rbox2(u, v, u0, u1, v0, v1, r):
    """2D box [u0,u1] x [v0,v1] with corners rounded to r."""
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    qu = np.abs(u - cu) - ((u1 - u0) / 2 - r)
    qv = np.abs(v - cv) - ((v1 - v0) / 2 - r)
    return np.hypot(np.maximum(qu, 0), np.maximum(qv, 0)) + np.minimum(np.maximum(qu, qv), 0) - r


def poly2(u, v, pts):
    """Signed distance to a closed 2D polygon (any winding)."""
    pts = np.asarray(pts, float)
    d = None
    s = np.ones_like(u)
    for i in range(len(pts)):
        a, b = pts[i - 1], pts[i]
        e = b - a
        wu, wv = u - a[0], v - a[1]
        t = np.clip((wu * e[0] + wv * e[1]) / (e @ e), 0, 1)
        dd = (wu - e[0] * t) ** 2 + (wv - e[1] * t) ** 2
        d = dd if d is None else np.minimum(d, dd)
        c1 = v >= a[1]
        c2 = v < b[1]
        c3 = e[0] * wv > e[1] * wu
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
    return s * np.sqrt(d)


_PROFILES = {}


def wall_profile(r, z, table, slopes):
    """Signed distance to the solid r <= R(z) of a revolved wall.

    R(z) is a cubic spline through the measured table, joining the linear extrapolations
    at both ends with matching slope, so the wall is smooth (no kinks between points)."""
    key = id(table)
    if key not in _PROFILES:
        zt, rt = np.array(table, float).T
        spl = CubicSpline(zt, rt, bc_type=((1, slopes[0]), (1, slopes[1])))
        zz = np.arange(zt[0], zt[-1] + 1e-9, 0.05)
        _PROFILES[key] = (zz, spl(zz), spl(zz, 1), slopes)
    zz, rr, dr, (lo, hi) = _PROFILES[key]
    R = np.interp(z, zz, rr) + lo * np.minimum(z - zz[0], 0) + hi * np.maximum(z - zz[-1], 0)
    k = np.interp(z, zz, dr)
    return (r - R) / np.sqrt(1 + k * k)


def end_arc(x, y, z, s, e):
    """Signed distance to the end surface x(y, z) of the bar or a pocket (negative inside)."""
    t = z + 10.5
    c = np.maximum(e["C0"] + e["KC"] * t, 1e-4)
    g = np.sqrt(1 + (c * y) ** 2 + (e["KX"] - e["KC"] * y * y / 2) ** 2)
    return (s * x - (e["X0"] + e["KX"] * t - c * y * y / 2)) / g


def box3(x, y, z, lo, hi):
    c = [(a + b) / 2 for a, b in zip(lo, hi)]
    h = [(b - a) / 2 for a, b in zip(lo, hi)]
    q = [np.abs(p - cc) - hh for p, cc, hh in zip((x, y, z), c, h)]
    out = np.sqrt(sum(np.maximum(qq, 0) ** 2 for qq in q))
    return out + np.minimum(np.maximum(np.maximum(q[0], q[1]), q[2]), 0)


# ------------------------------------------------------------- the knob

def fields(x, y, z):
    """Signed distances of the body, the raised pointer, and the pin holes and pins."""
    r = np.hypot(x, y)
    ay = np.abs(y)
    fo = wall_profile(r, z, SKIRT_OUT, SKIRT_SLOPES["out"])   # outer skirt wall
    fi = wall_profile(r, z, SKIRT_IN, SKIRT_SLOPES["in"])     # inner skirt wall

    # outside: skirt with the front disc and back rim, plus the grip bar
    # The side surface is one continuous field: the curved bar ends low down, blending
    # into the skirt wall over the 2.5 mm below the disc, so the bar's end face runs
    # smoothly into the skirt with no seam.
    # The skirt wall applies at and above the disc and beside the bar.
    def smooth(t):
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)
    ends = np.maximum(end_arc(x, y, z, 1, BAR_END), end_arc(x, y, z, -1, BAR_END))
    w_bar = W_BAR + K_BAR * (z + 27.5)
    w = np.maximum(smooth((z - (Z_DISC - 2.5)) / 2.5), smooth((ay - (w_bar + 0.5)) / 1.0))
    lateral = w * fo + (1 - w) * ends
    bar = i_round(drafted(ay, w_bar, K_BAR), Z_FRONT - z, R_BAR_FRONT)
    front = u_round(Z_DISC - z, bar, R_BAR_DISC)    # disc plus bar, filleted where they meet
    outer = i_round(lateral, front, R_OUTER_EDGE)
    outer = i_round(outer, z - Z_RIM, R_RIM_OUT)

    # inside: the cup and the two bar pockets as one cavity
    cup = i_round(fi, Z_FLOOR - z, R_FLOOR)
    side = drafted(ay, W_PKT + K_PKT * (z + 24.5), K_PKT)
    end = X_PKT + K_PKT_END * (z + 24.5)
    pockets = None
    # the pocket ends blend into the cup wall over the last 3 mm below the floor, so the
    # wall runs on without a step or line
    w_floor = np.clip((z - (Z_FLOOR - 3.0)) / 3.0, 0, 1)
    w_floor = w_floor * w_floor * (3 - 2 * w_floor)
    near_end = None
    for s in (-1, 1):
        p = i_round(side, drafted(end, s * x, K_PKT_END), R_POCKET_CORNER)
        pe_arc = end_arc(x, y, z, s, POCKET_END)
        pe = (1 - w_floor) * pe_arc + w_floor * fi
        p = i_round(p, pe, R_POCKET_END)
        p = i_round(p, Z_PB - z, R_POCKET)
        p = np.maximum(p, z - (Z_FLOOR + 1.5))
        pockets = p if pockets is None else np.minimum(pockets, p)
        near_end = pe_arc if near_end is None else np.maximum(near_end, pe_arc)
    # round the pocket mouths along the sides only; at the ends the pocket wall simply
    # continues the cup wall
    cavity = u_round(cup, pockets, R_POCKET_MOUTH * np.clip(-near_end / 1.5, 0, 1))
    body = d_round(outer, cavity, R_RIM_IN)

    # shaft sleeve
    tube = i_round(r - R_TUBE, z - Z_TUBE, R_TUBE_TOP)
    tube = np.maximum(tube, (Z_PB - 0.5) - z)   # ends 2.25 mm behind the bar front, out of the fillet's reach
    body = u_round(body, tube, R_TUBE_BASE + (R_TUBE_POCKET - R_TUBE_BASE) * np.clip((Z_PB + 1.75 - z) / 1.0, 0, 1))

    # pointer block (stepped, x-z profile) and its narrow tip, rib in the left pocket
    zb = Z_PB - 1.5
    x_wall = np.maximum(end_arc(x, y, z, 1, POCKET_END), end_arc(x, y, z, -1, POCKET_END)) - 1.2
    prof = u_round(rbox2(x, z, BLOCK_LOW["x0"], 40, zb, BLOCK_LOW["top"], R_BLOCK),
                   rbox2(x, z, BLOCK_HIGH["x0"], 40, zb, BLOCK_HIGH["top"], R_BLOCK), R_BLOCK_BASE)
    block = i_round(prof, ay - BLOCK_LOW["half_w"], R_BLOCK)
    tip = i_round(rbox2(x, z, BLOCK_TIP["x0"], 40, zb, BLOCK_TIP["top"], R_BLOCK),
                  ay - BLOCK_TIP["half_w"], R_BLOCK)
    block = u_round(block, tip, R_BLOCK_BASE)
    body = u_round(body, np.maximum(block, x_wall), R_BLOCK_BASE)
    for f in (WEDGE, PAD):
        y0, y1 = f["y"]
        body = np.minimum(body, np.maximum(poly2(x, z, f["pts"]), np.abs(y - (y0 + y1) / 2) - (y1 - y0) / 2))
    body = np.maximum(body, -box3(x, y, z, (SLOT["x"][0], SLOT["y"][0], SLOT["bottom"]), (SLOT["x"][1], SLOT["y"][1], 0.0)))
    rib = drafted(ay, RIB["half_w"] + RIB["draft"] * (RIB["top"] - z), -RIB["draft"])
    rib = np.maximum(np.maximum(rib, z - RIB["top"]), np.maximum(x - RIB["x1"], zb - z))
    e = RIB_END
    boss = np.maximum(np.hypot(x - e["x"], y - e["y"]) - e["r"],
                      drafted(z, e["z_hi"] + e["slope"] * (x - e["x_hi"]), e["slope"]))
    boss = np.maximum(boss, zb - z)
    body = np.minimum(body, np.maximum(np.minimum(rib, boss), x_wall))
    (dx0, dx1), (hw0, hw1) = RIB_DIP["x"], RIB_DIP["half_w"]
    dip_w = hw0 + (hw1 - hw0) * np.clip((x - dx0) / (dx1 - dx0), 0, 1)
    body = np.maximum(body, -np.maximum(poly2(x, z, RIB_DIP["pts"]), ay - dip_w))

    # bore
    rb = BORE_R + BORE_K * (np.minimum(z, BORE_Z_STRAIGHT) + 24.0)
    bore = i_round(drafted(r, rb, BORE_K), Z_BORE - z, R_BORE_BOTTOM)
    body = d_round(body, bore, R_TUBE_TOP)

    # raised pointer: an L-shaped strip 0.96 mm thick over the bar's +x end and front
    bar_end = end_arc(x, y, z, 1, BAR_END)
    t_end = PTR_END_T[0] + PTR_END_T[1] * np.maximum(-10.0 - z, 0)
    ptr = i_round(bar_end - t_end, (Z_FRONT - PTR_PROUD) - z, PTR_BEND)
    ptr = i_round(ptr, ay - PTR_HALF_W, R_PTR_EDGE)
    ptr = i_round(ptr, PTR_FRONT_X - x, R_PTR_EDGE)
    ptr = i_round(ptr, z - PTR_TOP, R_PTR_EDGE)
    core = np.maximum(bar_end + 1.0, (Z_FRONT + 1.0) - z)
    ptr = np.maximum(ptr, -core)                         # a shell, not a solid wedge

    # locating pins (on the pointer) and holes (in the body)
    xe = BAR_END["X0"] + BAR_END["KX"] * (PIN_END_Z + 10.5)
    h = PIN / 2
    pins = np.minimum(
        box3(x, y, z, (PIN_FRONT_X - h, -h, Z_FRONT - 0.5), (PIN_FRONT_X + h, h, Z_FRONT + PIN_LEN)),
        box3(x, y, z, (xe - PIN_LEN, -h, PIN_END_Z - h), (xe + 0.5, h, PIN_END_Z + h)))
    h += PIN_CLEAR
    holes = np.minimum(
        box3(x, y, z, (PIN_FRONT_X - h, -h, Z_FRONT - 1), (PIN_FRONT_X + h, h, Z_FRONT + PIN_LEN + 0.2)),
        box3(x, y, z, (xe - PIN_LEN - 0.2, -h, PIN_END_Z - h), (xe + 1, h, PIN_END_Z + h)))
    return body, ptr, pins, holes


def sample(res):
    """Evaluate the fields on a grid, in z slabs to bound memory."""
    lo = np.array([-30.6, -30.6, Z_FRONT - PTR_PROUD - 0.6])
    hi = np.array([30.6, 30.6, Z_TUBE + 0.6])
    n = np.ceil((hi - lo) / res).astype(int) + 1
    xs, ys, zs = (lo[i] + res * np.arange(n[i]) for i in range(3))
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    vols = {k: np.empty(n, np.float32) for k in ("knob", "body", "pointer")}
    for k0 in range(0, n[2], 16):
        k1 = min(k0 + 16, n[2])
        Z = zs[k0:k1]
        x = np.repeat(X[:, :, None], k1 - k0, 2)
        y = np.repeat(Y[:, :, None], k1 - k0, 2)
        z = np.broadcast_to(Z, x.shape)
        body, ptr, pins, holes = fields(x, y, z)
        vols["knob"][:, :, k0:k1] = np.minimum(body, ptr)
        vols["body"][:, :, k0:k1] = np.maximum(body, -holes)
        vols["pointer"][:, :, k0:k1] = np.minimum(np.maximum(ptr, -body), pins)
    log(f"sampled {n[0]}x{n[1]}x{n[2]} grid at {res} mm")
    return vols, lo


def mesh(vol, lo, res, faces):
    v, f, _, _ = measure.marching_cubes(vol, 0.0, spacing=(res, res, res))
    v += lo
    if len(f) > faces:
        v, f = fast_simplification.simplify(v.astype(np.float32), f.astype(np.int32),
                                            target_reduction=1 - faces / len(f))
    t = trimesh.Trimesh(v, f, process=False)
    if t.volume < 0:
        t.invert()
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--res", type=float, default=0.08)
    ap.add_argument("--faces", type=int, default=600_000)
    ap.add_argument("--scan-frame", action="store_true",
                    help="also write knob_scanframe.stl in the measurement frame (for verify_knob.py)")
    a = ap.parse_args()
    out = Path(a.outdir)
    vols, lo = sample(a.res)
    knob = mesh(vols.pop("knob"), lo, a.res, a.faces)
    body = mesh(vols.pop("body"), lo, a.res, a.faces)
    ptr = mesh(vols.pop("pointer"), lo, a.res, 20_000)
    log("meshed")

    dz = -Z_FRONT
    meshes = {}
    if a.scan_frame:
        meshes["knob_scanframe.stl"] = knob.copy()
    for name, t in (("knob.stl", knob), ("knob_body.stl", body)):
        t.apply_translation((0, 0, dz))
        meshes[name] = t
    # pointer: lay it on its flat side for printing
    ptr.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (1, 0, 0)))
    ptr.apply_translation(-ptr.bounds[0])
    meshes["knob_pointer.stl"] = ptr

    info = {}
    for name, t in meshes.items():
        t.export(out / name)
        if name == "knob_scanframe.stl":
            continue
        info[name] = {"faces": len(t.faces), "watertight": bool(t.is_watertight),
                      "volume_mm3": round(float(t.volume), 1),
                      "extents_mm": [round(float(v), 3) for v in t.extents]}
        print(name, info[name])
    info["resolution_mm"] = a.res
    (out / "knob.build.json").write_text(json.dumps(info, indent=2) + "\n")
    log("done")


if __name__ == "__main__":
    main()
