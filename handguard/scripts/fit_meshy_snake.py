"""Fit the Meshy-generated snake to the rebuilt handguard as two removable slide-on pieces.

Meshy (image-to-3D from the customer's concept picture, work/meshy/in_snake_hg.jpg) returns
the whole thing as one mesh: its own guess of a handguard, rail, front sight, receiver stub and
muzzle device, with the snake coiled around them. Only the snake is used. Steps:

1. Frame: the bore axis is fitted to Meshy's barrel (circle fits, t = 180..620) and muzzle
   device; t runs along it toward the muzzle. Meshy's handguard spans t = -290..1001, which
   maps onto our 387.4 mm handguard: scale 0.300 mm per unit. At that scale Meshy's handguard
   matches ours on the sides (radius 19-20 mm) and its rail top is within 1 mm of ours.
2. Radial fit: Meshy imagined a bottom rail about 8 mm deeper than our flat bottom, so every
   point is moved radially by (our surface radius - Meshy's surface radius) at its angle,
   smoothed around the axis and faded out over the head. The coils then rest on our handguard.
3. Voxelize the mesh (winding-number column rasterizer, robust to Meshy's two open edges) at
   0.25 mm and keep only what lies more than GAP mm outside our handguard: that removes Meshy's
   handguard and rail. The front sight, the receiver stub and the muzzle device are removed too.
4. Pads: the band between our handguard and GAP is filled wherever the snake is within reach,
   so every coil bears on the handguard.
5. Mesh, then (exact CSG) cut the slide-on envelope with running clearance, the 31 mm barrel
   passage through the head and the M5 lock screw, and split into rear and front pieces.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import trimesh
from manifold3d import Manifold
from scipy import ndimage as ndi
from shapely import contains_xy
from shapely.geometry import Polygon
from skimage.measure import marching_cubes

import build_handguard as HG
import build_snake as BS

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "wheel-cap", "scripts"))
from build_cap import rasterize  # noqa: E402

# ---- Meshy frame (fitted on work/meshy/snake_hg/stl.stl) ----
AXIS_P0 = np.array([400.0, -0.5, -33.5])       # a point on the barrel axis, Meshy units
AXIS_P1 = np.array([-950.0, -0.5, -30.3])      # centre of the muzzle device
SCALE = 0.300                                  # mm per Meshy unit
T_END = 1001.0                                 # Meshy t of the handguard's muzzle end
SIGHT_T = (560.0, 820.0)                       # Meshy front sight (removed)

GAP = 1.6          # what lies closer than this to our handguard is Meshy's handguard (removed)
GAP_TOP = 3.5      # same, over the rail, where Meshy's rail teeth stand taller than ours
H = 0.25           # voxel size
HEAD_FADE = (360.0, 378.0)
HEAD_CLEAN_X = 350.0  # from here forward, flakes thinner than CLEAN_T are removed (Meshy blend edges)
CLEAN_T = 1.2         # mm: three nozzle widths; anything thinner prints as loose strands   # radial fit fades out over this X range (the head keeps its shape)


def meshy_frame():
    d = (AXIS_P1 - AXIS_P0) / np.linalg.norm(AXIS_P1 - AXIS_P0)
    ez = np.array([0, 0, 1.0]) - d * d[2]; ez /= np.linalg.norm(ez)
    ey = np.cross(ez, d)
    return np.vstack([d, ey, ez])


# ---- our handguard's outer profile ----
def profile_polys():
    def polys(cs):
        return [Polygon(p) for p in cs.to_polygons()]
    circle = HG.CrossSection.circle(HG.R_OUT, HG.SEG)
    flats = HG.CrossSection.square((2 * HG.FLAT_SIDE, 2 * HG.R_OUT + 2)).translate((-HG.FLAT_SIDE, -HG.FLAT_BOT))
    keel = HG.CrossSection.square((2 * 14.0, 20.0)).translate((-14.0, -33.0))
    front = (circle ^ flats) + HG.rail_profile()
    rear = circle + HG.rail_profile() + keel
    return polys(front), polys(rear)


def surface_radius(polys, th):
    """Distance from the axis to the outer edge of the profile along angle th (0 = up, +90 = +Y)."""
    r = np.linspace(0, 45, 4501)
    out = np.zeros(len(th))
    for i, t in enumerate(th):
        y, z = r * np.sin(t), r * np.cos(t)
        inside = np.zeros(len(r), bool)
        for p in polys:
            inside |= contains_xy(p, y, z)
        out[i] = r[np.flatnonzero(inside).max()] if inside.any() else 0
    return out


def radial_correction(V, F, front_polys):
    """Per-angle shift (ours - Meshy's handguard surface radius), measured on X 70..350
    from area-weighted surface samples (flat faces such as the rail top have few vertices)."""
    P, _ = trimesh.sample.sample_surface(trimesh.Trimesh(V, F, process=False), 3_000_000, seed=0)
    X, Y, Z = P.T
    r = np.hypot(Y, Z); th = np.arctan2(Y, Z)
    k = (X > 70) & (X < 350)
    nb = 180
    ib = ((th[k] + np.pi) / (2 * np.pi) * nb).astype(int) % nb
    ix = ((X[k] - 70) / 1.0).astype(int)
    rmax = np.zeros((nb, 281)); np.maximum.at(rmax, (ib, ix), r[k])
    rmax[rmax == 0] = np.nan
    rm = np.nanpercentile(rmax, 15, axis=1)
    thc = (np.arange(nb) + 0.5) / nb * 2 * np.pi - np.pi
    ok = np.isfinite(rm)
    rm = np.interp(thc, thc[ok], rm[ok], period=2 * np.pi)
    ro = surface_radius(front_polys, thc)
    delta = np.clip(ro - rm, -10.0, 3.0)
    # circular smoothing (sigma 12 deg)
    delta = ndi.gaussian_filter1d(delta, sigma=12 / 2.0, mode="wrap")
    return thc, delta, rm, ro


def transform(V):
    R = meshy_frame()
    W = (V - AXIS_P0) @ R.T
    X = (W[:, 0] - T_END) * SCALE + HG.X_END
    return np.c_[X, W[:, 1] * SCALE, W[:, 2] * SCALE]


def apply_radial(V, thc, delta):
    X, Y, Z = V.T
    r = np.hypot(Y, Z); th = np.arctan2(Y, Z)
    dr = np.interp(th, thc, delta, period=2 * np.pi) * (1 - BS.smoothstep(*HEAD_FADE, X))
    s = (r + dr) / np.maximum(r, 1e-9)
    return np.c_[X, Y * s, Z * s]


# ---- the body: one continuous spiral (Meshy's coils stop at the rail and the flat bottom) ----
HELIX_X = (64.0, 384.0)    # starts behind the rear clamp block, ends inside Meshy's head
HELIX_TURNS = 4.0
HELIX_THETA0 = 100.0       # deg, 0 = top (rail), +90 = left side
R_HELIX = 9.5              # body radius
HELIX_EMBED = 0.3          # fraction of the body radius below the handguard surface (cut off as the belly)
TAIL_X0 = 10.0             # tail tip: the spiral continues backward from HELIX_X[0], tapering to a point
TAIL_RATE = 2.6            # deg/mm the tail turns (the body turns 4.5 deg/mm); it stays off the clamp below
TAIL_TIP_R = 1.25           # tip radius (2.5 mm thick tip prints cleanly with a 0.4 mm nozzle)
MESHY_HEAD_X = (368.0, 384.0)   # Meshy's model fades in over this X range (only its head is used)


class HelixBody(BS.Body):
    """A swept, scaled snake body along a helix around the bore axis. At each angle the
    helix sits on the handguard's outer surface (the max over a small angular window, so it
    rides over the rail rather than into it)."""

    def __init__(self, front_polys, rear_polys, step=0.1):
        nb = 720
        thb = (np.arange(nb) + 0.5) / nb * 2 * np.pi - np.pi
        win = int(round(8 / 360 * nb))
        def surf(polys):
            r = surface_radius(polys, thb)
            return np.max([np.roll(r, k) for k in range(-win, win + 1)], axis=0)
        sf, sr = surf(front_polys), surf(rear_polys)
        x0, x1 = HELIX_X
        x = np.linspace(TAIL_X0, x1, 250001)
        body_rate = 360.0 * HELIX_TURNS / (x1 - x0)
        rate = TAIL_RATE + (body_rate - TAIL_RATE) * BS.smoothstep(x0 - 30.0, x0 + 10.0, x)
        deg = np.r_[0, np.cumsum(0.5 * (rate[1:] + rate[:-1]) * np.diff(x))]
        deg += HELIX_THETA0 - np.interp(x0, x, deg)      # the body still starts at HELIX_THETA0
        th = np.radians(deg)
        thw = np.angle(np.exp(1j * th))
        rs = np.where(x < BS.STEP_X, np.interp(thw, thb, sr, period=2 * np.pi), np.interp(thw, thb, sf, period=2 * np.pi))
        # smooth the steps of the profile along the path (max filter first, so it never sinks in)
        rs = ndi.gaussian_filter1d(ndi.maximum_filter1d(rs, 4001), 1500)
        rho = rs + (1 - HELIX_EMBED) * R_HELIX
        C = np.c_[x, rho * np.sin(th), rho * np.cos(th)]
        seg = np.linalg.norm(np.diff(C, axis=0), axis=1)
        sc = np.r_[0, np.cumsum(seg)]
        self.s = np.arange(0, sc[-1], step)
        self.C = np.c_[[np.interp(self.s, sc, C[:, k]) for k in range(3)]].T
        # tail: tapers from the tip to full thickness where the body proper begins
        s_body = np.interp(x0, self.C[:, 0], self.s)
        t = np.clip(self.s / s_body, 0, 1)
        self.r = TAIL_TIP_R + (R_HELIX - TAIL_TIP_R) * t ** 1.15   # an even taper to the tip
        self.T, self.N, self.B = BS.frames(self.C)
        self.tree = BS.cKDTree(self.C)
        self.L = self.s[-1]
        # larger, deeper keeled scales, close to Meshy's
        self.scale_n, self.scale_row, self.scale_depth, self.keel_h = 14, 4.2, 0.9, 0.35
        # on the tail the scales shrink with the radius and fade out only near the tip
        ds = np.gradient(self.s)
        self.phase = np.cumsum(ds * R_HELIX / np.maximum(self.r, 2.0))
        self.phase -= np.interp(s_body, self.s, self.phase) - s_body
        self.scale_fade = (1.2, 2.6)
        self.depth_r = 6.0


def helix_occ(body, X3, Yg, Zg):
    P = np.stack(np.broadcast_arrays(X3, Yg[None], Zg[None]), -1).reshape(-1, 3)
    r = np.hypot(P[:, 1], P[:, 2])
    near = (r > 12.0) & (P[:, 0] > TAIL_X0 - R_HELIX - 1) & (P[:, 0] < HELIX_X[1] + R_HELIX + 1)
    occ = np.zeros(len(P), np.float32)
    if near.any():
        d = body.sdf(P[near])
        occ[near] = np.clip(0.5 - d / H, 0, 1)
    return occ.reshape(np.broadcast_shapes(X3.shape, Yg[None].shape))


# ---- voxel stage ----
def build_field(V, F, front_polys, rear_polys, x_range=(HG.X_FACE, 452.0), slab=30.0):
    body = HelixBody(front_polys, rear_polys)
    y0, y1, z0, z1 = -44.0, 44.0, -44.0, 52.0
    ys = y0 + np.arange(int((y1 - y0) / H) + 1) * H
    zs = z0 + np.arange(int((z1 - z0) / H) + 1) * H
    Yg, Zg = np.meshgrid(ys, zs, indexing="ij")
    # signed distance outside our profile (2-D, per section type)
    def dist_out(polys):
        inside = np.zeros(Yg.shape, bool)
        for p in polys:
            inside |= contains_xy(p, Yg, Zg)
        return np.where(inside, -ndi.distance_transform_edt(inside), ndi.distance_transform_edt(~inside)) * H
    d_front, d_rear = dist_out(front_polys), dist_out(rear_polys)
    xs_all = x_range[0] + np.arange(int((x_range[1] - x_range[0]) / H) + 1) * H
    halo = int(np.ceil((GAP + 1.5) / H)) + 2
    nsl = int(slab / H)
    tri_lo = V[F][:, :, 0].min(1); tri_hi = V[F][:, :, 0].max(1)
    fields = []
    t0 = time.time()
    for a in range(0, len(xs_all), nsl):
        lo = max(0, a - halo); hi = min(len(xs_all), a + nsl + 1 + halo)
        xs = xs_all[lo:hi]
        sel = (tri_hi >= xs[0] - H) & (tri_lo <= xs[-1] + H)
        grid = dict(x0=xs[0], y0=ys[0], z0=zs[0], h=H, nx=len(xs), ny=len(ys), nz=len(zs))
        Ff = F[sel]
        occ = rasterize(V, Ff, grid)
        if occ.max() <= 0:
            occ = rasterize(V, Ff, grid, flip=True)
        X3 = xs[:, None, None]
        d_env = np.where(X3 < BS.STEP_X, d_rear[None], d_front[None])
        r3 = np.hypot(Yg, Zg)[None]
        # what is Meshy's own hardware, not snake
        t = (X3 - HG.X_END) / SCALE + T_END
        sight = (t > SIGHT_T[0]) & (t < SIGHT_T[1]) & (np.abs(Yg)[None] < 9.0) & (Zg[None] > HG.RAIL_TOP - 1.0)
        muzzle = (X3 > HG.X_END - 0.5) & (r3 < BS.PASSAGE_R)
        gap = np.where((np.abs(Yg) < 13.0) & (Zg > 24.0), GAP_TOP, GAP)[None]
        # in front of the handguard there is no handguard to strip: only the barrel passage
        keep = ((d_env > gap) | (X3 > HG.X_END + BS.CLEARANCE)) & ~sight & ~muzzle & (X3 > HG.X_FACE + 3.0)
        snake = np.where(keep, occ, 0.0).astype(np.float32)
        snake = snake * BS.smoothstep(*MESHY_HEAD_X, X3)   # tapers the back of the head instead of a flat cut
        # pads: fill the band between the handguard and the trimmed snake, but only straight
        # under a coil (looking radially outward), so every coil bears on the handguard
        band = (d_env >= -0.5) & (d_env <= gap + 0.5) & (X3 > HG.X_FACE + 3.0) & (X3 < HG.X_END)
        pad = np.zeros(snake.shape, np.float32)
        bi = np.nonzero(band)
        if len(bi[0]):
            yb, zb = ys[bi[1]], zs[bi[2]]
            rb = np.maximum(np.hypot(yb, zb), 1e-6)
            hit = np.zeros(len(yb), bool)
            for dlt in np.arange(0.5, GAP_TOP + 1.6, 0.5):
                f = (rb + dlt) / rb
                c = np.vstack([bi[0], (yb * f - ys[0]) / H, (zb * f - zs[0]) / H])
                hit |= ndi.map_coordinates(snake, c, order=1, mode="constant") > 0.5
            pad[bi[0][hit], bi[1][hit], bi[2][hit]] = 1.0
        pad = ndi.gaussian_filter(pad, 0.6)
        field = np.maximum(np.maximum(snake, pad), hinge_occ(X3, Yg, Zg))
        field = np.maximum(field, helix_occ(body, X3, Yg, Zg))
        if xs[-1] > HEAD_CLEAN_X:
            solid = field > 0.5
            kept = ndi.binary_opening(solid, structure=ball(CLEAN_T / 2))
            flakes = solid & ~kept & (X3 > HEAD_CLEAN_X)
            field = np.where(flakes, 0.0, field).astype(np.float32)
        # rear clamp: cross bolts, centre screw and slit stay free
        field = np.where((X3 < 64.0) & (Zg[None] < -14.0), 0.0, field)
        fields.append(field[a - lo: a - lo + min(nsl, len(xs_all) - a)])
        print(f"  voxel slab X {xs_all[a]:.0f}..{xs_all[min(a + nsl, len(xs_all) - 1)]:.0f}  {time.time() - t0:.0f}s", flush=True)
    vol = np.concatenate(fields, axis=0)
    # drop anything the flake removal cut loose
    lab, n = ndi.label(vol > 0.5, structure=np.ones((3, 3, 3)))
    if n > 1:
        sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1)) * H ** 3
        loose = np.isin(lab, 1 + np.flatnonzero(sizes < 0.2 * sizes.max()))
        print(f"  removed {int((sizes < 0.2 * sizes.max()).sum())} loose bits, {sizes[sizes < 0.2 * sizes.max()].sum():.1f} mm3")
        vol = np.where(loose, 0.0, vol).astype(np.float32)
    return vol, (xs_all[0], ys[0], zs[0])


def ball(r):
    n = int(np.ceil(r / H))
    g = np.mgrid[-n:n + 1, -n:n + 1, -n:n + 1] * H
    return (g ** 2).sum(0) <= r * r + 1e-9


def strip_slivers(tm):
    """Remove zero-area shells the booleans leave where the belly cut meets the handguard's
    flat faces. They only separate once coincident vertices are merged (as most slicers do on
    import), so find them on a merged copy and delete just those triangles from the original."""
    merged = tm.copy()
    merged.merge_vertices()
    comps = trimesh.graph.connected_components(merged.face_adjacency, nodes=np.arange(len(merged.faces)))
    areas = merged.area_faces
    drop = np.concatenate([c for c in comps if areas[c].sum() < 1.0] or [np.zeros(0, int)])
    if len(drop):
        keep = np.ones(len(tm.faces), bool); keep[drop] = False
        tm = trimesh.Trimesh(tm.vertices, tm.faces[keep], process=False)
        tm.remove_unreferenced_vertices()
    return tm, len(drop)


CHEEKS = [((388.0, s * 17.0, -6.0), (401.0, s * 12.5, -22.0), 6.0) for s in (1, -1)]  # jaw hinges
THROAT = (HG.X_END + BS.CLEARANCE, HG.X_END + 6.0, 20.0)   # X range and outer radius of the solid stop ring


def hinge_occ(X3, Yg, Zg):
    """Occupancy of the two scaled jaw hinges (the barrel passage cuts Meshy's jaw off at the middle)."""
    P = np.stack(np.broadcast_arrays(X3, Yg[None], Zg[None]), -1).reshape(-1, 3)
    near = (P[:, 0] > 378.0) & (P[:, 0] < 412.0) & (P[:, 2] < 4.0) & (np.abs(P[:, 1]) > 4.0)
    occ = np.zeros(len(P), np.float32)
    if near.any():
        Q = P[near]
        d = np.minimum.reduce([BS.capsule(Q, a, b, ra, ra) for a, b, ra in CHEEKS])
        d1, d2, f1 = BS.worley(Q * np.array([0.75, 1.0, 1.0]), BS.HEAD_CELL)
        edge = BS.smoothstep(0.0, 0.3 * BS.HEAD_CELL, d2 - d1)
        lift = np.clip(0.5 - (Q[:, 0] * 0.75 - f1[:, 0]) / BS.HEAD_CELL, 0, 1)
        d = d + BS.HEAD_DEPTH * (1 - edge * (0.45 + 0.55 * lift))
        occ[near] = np.clip(0.5 - d / H, 0, 1)
    return occ.reshape(np.broadcast_shapes(X3.shape, Yg[None].shape))


def mesh_field(vol, origin):
    pad = np.pad(vol, 1, constant_values=0.0)
    v, f, _, _ = marching_cubes(pad, 0.5, spacing=(H, H, H))
    v = v + np.array(origin) - H
    m = trimesh.Trimesh(v, f[:, ::-1], process=False)   # inside = high values: flip to outward normals
    if m.volume < 0:
        m.invert()
    m.merge_vertices(digits_vertex=4); m.update_faces(m.nondegenerate_faces()); m.remove_unreferenced_vertices()
    trimesh.repair.fill_holes(m)
    return m


def split_square_to_coil(snake, xc, r_local=15.0):
    """Split into rear and front pieces with the joint square to the coil, instead of along a
    plane across the bore (that cuts the coil at a shallow angle into feather-thin wedges).
    A ball around the coil's centreline where it crosses X = xc severs the coil; inside the
    ball the cut is the plane perpendicular to the centreline, and each half joins the side
    of the coil it touches (tail side -> rear piece, head side -> front piece)."""
    fp, rp = profile_polys()
    body = HelixBody(fp, rp)
    i = int(np.argmin(np.abs(body.C[:, 0] - xc)))
    p, t = body.C[i], body.T[i]
    print("joint: square to the coil at", p.round(1).tolist(), "tangent", t.round(3).tolist())
    ball = Manifold.sphere(r_local, 96).translate(tuple(p))
    rest = sorted((snake - ball).decompose(), key=lambda m: -m.volume())
    tail_side = min(rest[:2], key=lambda m: m.bounding_box()[0])
    head_side = max(rest[:2], key=lambda m: m.bounding_box()[0])
    local = snake ^ ball
    rear = tail_side + local.trim_by_plane(tuple(-t), float(-t @ p))
    front = head_side + local.trim_by_plane(tuple(t), float(t @ p))
    return {"rear": rear, "front": front}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meshy_stl", nargs="?", default=os.path.join(HERE, "..", "work", "meshy", "snake_hg", "stl.stl"))
    ap.add_argument("--split", type=float, default=209.4)
    ap.add_argument("--outdir", default=os.path.join(HERE, ".."))
    ap.add_argument("--tolerance", type=float, default=0.02)
    a = ap.parse_args()
    t0 = time.time()
    src = trimesh.load(a.meshy_stl)
    src.merge_vertices()
    V = transform(np.asarray(src.vertices, float)); F = np.asarray(src.faces)
    front_polys, rear_polys = profile_polys()
    thc, delta, rm, ro = radial_correction(V, F, front_polys)
    print("radial shift, mm: min %.1f  max %.1f  (bottom %.1f, sides %.1f, top %.1f)" % (
        delta.min(), delta.max(), delta[0], delta[len(delta) // 4], delta[len(delta) // 2]))
    V = apply_radial(V, thc, delta)
    vol, origin = build_field(V, F, front_polys, rear_polys)
    snake_tm = mesh_field(vol, origin)
    print("voxel snake:", len(snake_tm.faces), "faces, watertight", snake_tm.is_watertight, f"{time.time() - t0:.0f}s")
    snake_tm.export(os.path.join(HERE, "..", "work", "meshy_snake_raw.stl"))
    snake = BS.to_manifold(snake_tm) - BS.handguard_envelope()
    # barrel passage through the head
    # a solid ring inside the head where it rests on the handguard's muzzle end (it takes the
    # snake's weight whenever the rifle cycles), then the barrel passage through it
    throat = HG.cyl_x(THROAT[2], THROAT[0], THROAT[1])
    snake = snake + throat
    passage = HG.cyl_x(BS.PASSAGE_R, HG.X_END - 0.5, 470.0)
    snake = snake - passage
    # lock screw: down through the last coil that crosses the top rail, into the rail slot
    # under it (heat-set insert in the coil, set screw tip in the slot)
    x0 = origin[0]; iy = int(round((0.0 - origin[1]) / H))
    zs = origin[2] + np.arange(vol.shape[2]) * H
    best = None
    for k in range(HG.RAIL_SLOTS):
        xc = HG.RAIL_SLOT_X0 + k * HG.RAIL_PITCH
        if not (a.split + 12 < xc < HG.X_END - 10):
            continue
        cols = vol[int(round((xc - 3.5 - x0) / H)):int(round((xc + 3.5 - x0) / H)) + 1, iy - 14:iy + 15]
        solid = (cols > 0.5).all(axis=(0, 1))   # material over a 7 x 7 mm footprint
        z = np.flatnonzero(solid & (zs > HG.RAIL_TOP + 1.0))
        if len(z) == 0 or zs[z[0]] > HG.RAIL_TOP + 2.0:
            continue
        top = zs[z[0] + np.flatnonzero(np.diff(np.r_[z, -10]) != 1)[0]]
        if best is None or xc > best[0]:
            best = (xc, top)
    if best is None or best[1] - BS.LOCK_INSERT_L < HG.RAIL_TOP + BS.CLEARANCE + 2.0:
        raise SystemExit("no coil over the rail is thick enough for the lock screw")
    lock_x, top = best
    print(f"lock screw: rail slot at X={lock_x:.1f}, coil top Z={top:.2f} (rail top {HG.RAIL_TOP})")
    insert = Manifold.cylinder(BS.LOCK_INSERT_L + 8, BS.LOCK_INSERT_D / 2, BS.LOCK_INSERT_D / 2, 48) \
        .translate((lock_x, 0, top - BS.LOCK_INSERT_L))
    clear = Manifold.cylinder(top - HG.RAIL_TOP + 2, BS.LOCK_SCREW_D / 2, BS.LOCK_SCREW_D / 2, 48) \
        .translate((lock_x, 0, HG.RAIL_TOP - 1))
    snake = snake - insert - clear
    json.dump({"lock_x": lock_x, "coil_top": round(float(top), 2)}, open(os.path.join(HERE, "..", "data", "snake_lock.json"), "w"))
    if a.tolerance > 0:
        snake = snake.simplify(a.tolerance)
    base = HG.build(json.load(open(os.path.join(HERE, "..", "data", "hole_templates.json"))))
    pieces = split_square_to_coil(snake, a.split)
    for name, piece in pieces.items():
        parts = sorted(piece.decompose(), key=lambda p: -p.volume())
        big = [p for p in parts if p.volume() > 150.0]   # stray bits of Meshy's receiver and sight
        dropped = [round(p.volume(), 2) for p in parts if p.volume() <= 150.0]
        piece = big[0]
        for p in big[1:]:
            piece = piece + p
        tm, slivers = strip_slivers(HG.to_trimesh(piece))
        print(f"snake {name}: {len(big)} part(s), {slivers} slivers removed, faces {len(tm.faces)}, watertight {tm.is_watertight}, "
              f"volume {tm.volume / 1000:.1f} cm3, bounds {tm.bounds.round(1).tolist()}, dropped {dropped[:12]}")
        tm.export(os.path.join(a.outdir, f"snake_{name}.3mf"))
        pieces[name] = piece
    both = pieces["rear"] + pieces["front"]
    HG.to_trimesh(base + both).export(os.path.join(HERE, "..", "work", "assembled_preview.stl"))
    print("overlap between handguard and snake (mm3, must be 0):", round((base ^ both).volume(), 4))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
