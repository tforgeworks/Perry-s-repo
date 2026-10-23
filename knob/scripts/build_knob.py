"""Build a printable model of the chrome bar knob (mold mark 1439/A) from dimensions
measured on its 3D scan.

The knob is a drafted cup (skirt) with a hollow grip bar on the front and a shaft
sleeve in the middle. Every dimension below was measured on the aligned scan (see
README.md); the model is built from exact solids with manifold3d, so faces are flat
and walls are true, without scan noise.

Model frame (mm): z is the knob axis, +z toward the back (the appliance panel),
the bar runs along x, the red pointer is at +x. The output STLs are translated so
the bar's front face sits at z=0 (print orientation: front face down).

Usage: python build_knob.py --outdir ..
Writes knob.stl (one body), knob_body.stl + knob_pointer.stl (two-color set),
knob_2color.3mf and knob.build.json.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, OpType

SEG = 360  # circular segments for revolved surfaces (chord error < 0.002 mm)

# ------------------------------------------------------------- measured dimensions
# heights along the axis
Z_FRONT = -29.50   # front face of the grip bar
Z_DISC = -10.40    # front face of the round disc beside the bar
Z_FLOOR = -7.72    # floor inside the cup
Z_RIM = 9.70       # back rim of the skirt
Z_PB = -26.75      # bottom of the two bar pockets
Z_BORE = -26.85    # bottom of the shaft bore
Z_TUBE = 20.45     # back end of the shaft sleeve

# skirt: cones with 4.07 deg draft, r = R0 + K*z
K_CONE = 0.0711
RO0 = 28.211       # outer radius at z=0
RI0 = 25.616       # inner radius at z=0

# grip bar: half-widths with ~5.2 deg draft, w = W + K*(z - Zref)
def bar_half_width(z):
    return 10.58 + 0.0906 * (z + 27.5)


def pocket_half_width(z):
    return 8.17 + 0.0956 * (z + 24.5)


def pocket_inner_end(z):  # |x| of the pocket end next to the sleeve
    return 7.50 - 0.058 * (z + 24.5)


POCKET_CORNER = 1.5
BAR_FRONT_ROUND = 0.8
DISC_EDGE_ROUND = 1.0
RIM_ROUND = 0.45
FLOOR_FILLET = 0.4

# shaft sleeve
R_TUBE = 9.0


def bore_radius(z):  # 1.2 deg draft up to z=3, straight above
    return 7.0 + 0.02074 * (min(z, 3.0) + 24.0)


# red pointer: L-shaped strip on the bar's +x end face and front face
PTR_HALF_W = 1.9
PTR_PROUD = 0.96     # how far it stands off the end face
PTR_TOP = -8.4       # where it ends on the end face
PTR_FRONT_X = 14.0   # where it starts on the front face
PTR_INLAY = 1.0      # depth of the flush inlay in the front face


def r_out(z):
    return RO0 + K_CONE * z


def r_in(z):
    return RI0 + K_CONE * z


# ------------------------------------------------------------------- helpers

def arc(cx, cy, r, a0, a1, n=12):
    t = np.radians(np.linspace(a0, a1, n))
    return [(cx + r * np.cos(a), cy + r * np.sin(a)) for a in t]


def revolve(profile):
    """Revolve a (r, z) polygon (counter-clockwise) about the z axis."""
    return CrossSection([profile]).revolve(SEG)


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def layer(cs, z):
    return cs.extrude(1e-3).translate((0, 0, z))


def rounded_rect(x0, x1, y0, y1, r):
    sq = CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))
    return sq.offset(-r, JoinType.Round).offset(r, JoinType.Round, circular_segments=48)


def fillet_corner(p_in, p_corner, p_out, r, n=10):
    """Points of a circular fillet of radius r at a polygon corner."""
    p_in, p_corner, p_out = map(np.asarray, (p_in, p_corner, p_out))
    u = (p_in - p_corner) / np.linalg.norm(p_in - p_corner)
    v = (p_out - p_corner) / np.linalg.norm(p_out - p_corner)
    half = np.arccos(np.clip(u @ v, -1, 1)) / 2
    d = r / np.tan(half)
    a, b = p_corner + u * d, p_corner + v * d
    bis = (u + v) / np.linalg.norm(u + v)
    c = p_corner + bis * r / np.sin(half)
    a0 = np.arctan2(*(a - c)[::-1])
    a1 = np.arctan2(*(b - c)[::-1])
    da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
    return [tuple(c + r * np.array([np.cos(a0 + da * t), np.sin(a0 + da * t)]))
            for t in np.linspace(0, 1, n)]


def rounded_polygon(pts, radii):
    out = []
    n = len(pts)
    for i in range(n):
        if radii[i] > 0:
            out += fillet_corner(pts[i - 1], pts[i], pts[(i + 1) % n], radii[i])
        else:
            out.append(pts[i])
    return out


# ------------------------------------------------------------------- parts

def skirt_and_disc():
    """Drafted skirt plus the round front disc, as one revolved profile."""
    pts = [(0.0, Z_DISC), (r_out(Z_DISC), Z_DISC), (r_out(Z_RIM), Z_RIM),
           (r_in(Z_RIM), Z_RIM), (r_in(Z_FLOOR), Z_FLOOR), (0.0, Z_FLOOR)]
    radii = [0, DISC_EDGE_ROUND, RIM_ROUND, RIM_ROUND, FLOOR_FILLET, 0]
    return revolve(rounded_polygon(pts, radii))


def outer_cone(z0, z1, extra=0.0, front_round=0.0):
    pts = [(0.0, z0), (r_out(z0) + extra, z0), (r_out(z1) + extra, z1), (0.0, z1)]
    return revolve(rounded_polygon(pts, [0, front_round, 0, 0]))


def bar_outer():
    """Grip bar: drafted slab with rounded front side edges, ends on the skirt cone."""
    layers = []
    f = BAR_FRONT_ROUND
    for t in np.linspace(0, np.pi / 2, 9):
        z = Z_FRONT + f * (1 - np.sin(t))
        w = bar_half_width(z) - f * (1 - np.cos(t))
        layers.append(layer(CrossSection.square((70, 2 * w)).translate((-35, -w)), z))
    zt = Z_DISC + 0.5
    w = bar_half_width(zt)
    layers.append(layer(CrossSection.square((70, 2 * w)).translate((-35, -w)), zt))
    slab = Manifold.batch_hull(layers)
    return slab ^ outer_cone(Z_FRONT, zt, front_round=f)


def inner_cone(z0, z1):
    return revolve([(0.0, z0), (r_in(z0), z0), (r_in(z1), z1), (0.0, z1)])


def pockets():
    z0, z1 = Z_PB, Z_FLOOR + 0.5
    out = []
    for s in (-1, 1):
        ls = []
        for z in (z0, z1):
            xe, w = pocket_inner_end(z), pocket_half_width(z)
            rr = rounded_rect(xe, 40, -w, w, POCKET_CORNER)
            ls.append(layer(rr if s > 0 else rr.mirror((1, 0)), z))
        out.append(Manifold.batch_hull(ls))
    tube = Manifold.cylinder(z1 - z0 + 2, R_TUBE, R_TUBE, SEG).translate((0, 0, z0 - 1))
    return (Manifold.batch_boolean(out, op=OpType.Add)
            ^ inner_cone(z0 - 1, z1 + 1)) - tube


def sleeve():
    return Manifold.cylinder(Z_TUBE - (Z_PB - 0.5), R_TUBE, R_TUBE, SEG).translate((0, 0, Z_PB - 0.5))


def bore():
    zs = np.linspace(Z_BORE, 3.0, 12).tolist() + [Z_TUBE + 1]
    prof = [(0.0, Z_BORE)] + [(bore_radius(z), z) for z in zs] + [(0.0, Z_TUBE + 1)]
    return revolve(prof)


def ribs():
    zb = Z_PB - 0.2
    parts = [
        box(-24.2, -8.6, -1.75, 1.75, zb, -21.8),   # rib in the bottom of the left pocket
        box(15.5, 25.2, -4.0, 4.0, zb, -23.3),       # pointer block, stepped
        box(18.6, 25.2, -4.0, 4.0, zb, -21.4),
        box(20.45, 25.4, -4.1, 4.1, zb, -8.6),
        box(22.8, 25.6, -2.1, 2.1, zb, -4.7),
    ]
    return Manifold.batch_boolean(parts, op=OpType.Add) ^ outer_cone(Z_FRONT, 0)


def pointer():
    end_leg = (outer_cone(Z_FRONT, PTR_TOP, extra=PTR_PROUD)
               - outer_cone(Z_FRONT - 1, PTR_TOP + 1, extra=-0.3))
    end_leg = end_leg ^ box(0, 40, -PTR_HALF_W, PTR_HALF_W, Z_FRONT, PTR_TOP)
    front_leg = (box(PTR_FRONT_X, 40, -PTR_HALF_W, PTR_HALF_W, Z_FRONT, Z_FRONT + PTR_INLAY)
                 ^ outer_cone(Z_FRONT, Z_FRONT + PTR_INLAY, extra=PTR_PROUD))
    return end_leg + front_leg


def build():
    body = skirt_and_disc() + bar_outer()
    body = body - pockets()
    body = body + sleeve() + ribs()
    body = body - bore()
    ptr = pointer()
    whole = body + ptr
    return whole, whole - ptr, ptr


def to_trimesh(m, dz):
    mesh = m.to_mesh()
    t = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)
    t.apply_translation((0, 0, dz))
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--scan-frame", action="store_true",
                    help="also write knob_scanframe.stl in the measurement frame (for verify.py)")
    a = ap.parse_args()
    out = Path(a.outdir)
    whole, body, ptr = build()
    dz = -Z_FRONT
    meshes = {"knob.stl": to_trimesh(whole, dz), "knob_body.stl": to_trimesh(body, dz),
              "knob_pointer.stl": to_trimesh(ptr, dz)}
    if a.scan_frame:
        meshes["knob_scanframe.stl"] = to_trimesh(whole, 0)
    info = {}
    for name, t in meshes.items():
        t.export(out / name)
        if name == "knob_scanframe.stl":
            continue
        info[name] = {"faces": len(t.faces), "watertight": bool(t.is_watertight),
                      "volume_mm3": round(float(t.volume), 1),
                      "extents_mm": [round(float(v), 3) for v in t.extents]}
        print(name, info[name])
    scene = trimesh.Scene()
    scene.add_geometry(meshes["knob_body.stl"], node_name="knob_body", geom_name="knob_body")
    scene.add_geometry(meshes["knob_pointer.stl"], node_name="pointer", geom_name="pointer")
    (out / "knob_2color.3mf").write_bytes(trimesh.exchange.threemf.export_3MF(scene))
    (out / "knob.build.json").write_text(json.dumps(info, indent=2) + "\n")


if __name__ == "__main__":
    main()
