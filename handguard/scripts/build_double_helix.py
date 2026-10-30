"""The snake as built: two bodies wrapped around the handguard as a double helix, with Meshy's
head at the muzzle end.

Two bodies leave the back of the head, one on each side, and spiral back toward the receiver
in opposite directions: the snake is a mirror image left to right, seen from above. They cross
every 40 mm (under the handguard, over the top, under, ...), the upper body riding over the
lower one at each crossing, and end in two tails on the top shoulders at the rear. The bodies
are slightly flattened ellipses in section, 23 mm thick at the necks, 29 mm along the middle,
tapering to the tails; the centreline is one smooth curve (no straights, no kinks) that drapes
over the rail rather than following its edges.

Kept clear for the rifle's accessories (the coils are placed around these; nothing is cut):
  * the top rail right behind the head (front sight) and between the crossings over the top
  * the front bottom keymod slot (bipod mount)
  * the rear clamp (bolts, centre screw, slit) and the receiver end
  * the barrel passage (31 mm) straight through the head

The head comes from Meshy (image-to-3D of the concept, see fit_meshy_snake.py). It is turned
into a signed distance field so it can be blended into the necks with a wide fillet, its back
rounded, its lower (chin) fangs and its own fang stubs removed, its nose rounded off, and long
upper fangs added that grow from the roof of the mouth.

Two pieces, each under 256 mm, joined where the bodies are on the sides: four rectangular
tabs on the front piece slide into pockets in the rear piece. Each piece is bolted from the left
and the right by M5 screws (in heat-set inserts) into side keymod holes: the rear piece's at the
rear end of their holes, the front piece's at the front end.
"""
import argparse
import json
import os
import time

import numpy as np
import trimesh
from manifold3d import Manifold
from scipy import ndimage as ndi
from shapely import contains_xy

import build_handguard as HG
import build_snake as BS
import fit_meshy_snake as FM
from fit_meshy_snake import H, rasterize

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- body path ----
# Two bodies leave the back of the head, one on each side, and spiral back toward the receiver
# in opposite directions, mirror images of each other seen from above. They cross under the
# handguard, over the top and under again, and end in two tails on the top shoulders at the
# rear end. Everything below is for the left-hand body; the right one is its mirror (Y -> -Y).
K = 4.5                    # deg per mm the bodies turn: they cross every 40 mm (about 64 deg to the bore)
X_LAST = 338.0             # last crossing (underneath): from it the necks rise diagonally into the head
X_TC = 58.0                # last crossing over the top at the rear; behind it the tails ease out
X_TIP = 14.0               # tail tips, on the top shoulders at the rear end
TAIL_EASE = 4              # turning rate behind X_TC = K * smoothstep(X_TIP, X_TC) ** TAIL_EASE
FADE_N = (352.0, 392.0)    # the turning eases out as the necks enter the head
X_SPLIT = 238.0            # joint between the two pieces (the bodies are on the left and right sides here)
R_NECK = 11.5              # body radius where it enters the head (23 mm thick each)
R_MID = 14.5               # body radius along the middle (29 mm thick)
NECK_LEN = 70.0            # the body grows from the neck to its full thickness over this length
NECK_FLARE = (3.5, 28.0)   # ... and flares by this much over this length where it enters the head
HEAD_BLEND = 9.0           # fillet between the necks and the head (mm)
R_TIP = 1.4                # tail tip radius
TAPER_P = 5.0              # body radius = tip + (neck - tip) * (1 - (s / L) ** TAPER_P)
Q_BODY = 0.82              # body height / width where it lies on the handguard (round at the neck)
EMBED = 0.35               # fraction of the body height sunk into the handguard (cut off as the belly)
LIFT = 0.45                # at a crossing the upper body rides this fraction of both heights higher
SMOOTH = 10.0              # mm: the centreline is smoothed over this length, so it has no kinks
HEAD_TARGET = np.array([400.0, 9.0, 6.0])   # each neck ends inside the head here (Y on its own side)

# ---- keep-outs ----
SIGHT_X = (322.5, 370.5)   # top rail kept clear for a front sight, from the last top crossing to the head
SIGHT_YZ = (16.0, 24.0)    # ... over |Y| < 16 and Z > 24 (rail top 31.1)
BIPOD_X = (283.0, 314.0)   # bottom kept clear for the bipod at the front bottom keymod slot (306.95)
BIPOD_YZ = (12.0, -19.0)   # ... over |Y| < 12 and Z < -19 (bottom flat -18.55)

# ---- head ----
HEAD_GRID = dict(x=(352.0, 476.0), y=(-44.0, 44.0), z=(-46.0, 52.0), h=0.3)
LOW_FANG_HOLLOW = ((434.0, 0.0, -19.5), (15.5, 9.0, 10.0))   # chin fangs removed: a rounded hollow (centre, radii)
PALATE = ((443.5, 0.0, 0.0), (16.0, 18.6, 18.6))   # Meshy's own fang stubs removed: a smooth vault in the mouth roof
FANG = ((440.5, 14.6, 17.0), (443.5, 15.4, 9.5), (439.5, 16.4, 2.6))   # root (in the roof of the mouth), control, tip: they lie on one straight line across, so no sideways curve
FANG_ROOT_R, FANG_TIP_R = 2.7, 0.25
NOSE_TIP = (456.0, 0.0, 23.5)
NOSE = ((445.5, 0.0, 23.5), (9.0, 6.8, 5.4))   # rounded snout (centre, radii)


def hull_radius(polys, th):
    """Radius of the convex hull of the handguard profile along angle th, smoothed: the body
    drapes over the rail instead of following its edges (no kinks)."""
    from shapely.geometry import MultiPolygon
    from shapely.ops import unary_union
    hull = unary_union(MultiPolygon([p for p in polys]) if len(polys) > 1 else polys[0]).convex_hull
    r = FM.surface_radius([hull], th)
    return ndi.gaussian_filter1d(r, 12.0 / 360 * len(th), mode="wrap")


def path_xtheta():
    """Centreline of the left body in (X, theta deg; 0 = top, +90 = left), head end first."""
    x = np.linspace(X_TIP, FADE_N[1] + 1.0, 20001)
    rate = K * BS.smoothstep(X_TIP, X_TC, x) ** TAIL_EASE * (1 - BS.smoothstep(*FADE_N, x))
    cum = np.r_[0, np.cumsum(0.5 * (rate[1:] + rate[:-1]) * np.diff(x))]
    th = 180.0 + cum - np.interp(X_LAST, x, cum)
    # forward from the end of the spiral into the head
    xn = np.linspace(x[-1], HEAD_TARGET[0], 300)[1:]
    X = np.r_[x, xn][::-1]
    TH = np.r_[th, np.full(len(xn), th[-1])][::-1]
    lab = np.r_[np.full(len(x), 1), np.full(len(xn), 0)][::-1]
    return smooth_path(X, TH, lab)


def smooth_path(X, TH, lab, rho_ref=32.0, step=0.25):
    """Round every corner of the (X, theta) path with a Gaussian along its length. A helix is a
    straight line in (X, theta), so the spirals keep their shape exactly."""
    V = np.radians(TH) * rho_ref
    s = np.r_[0, np.cumsum(np.hypot(np.diff(X), np.diff(V)))]
    keep = np.r_[True, np.diff(s) > 1e-9]
    s, X, V, lab = s[keep], X[keep], V[keep], lab[keep]
    ss = np.arange(0, s[-1], step)
    Xs = ndi.gaussian_filter1d(np.interp(ss, s, X), SMOOTH / step, mode="nearest")
    Vs = ndi.gaussian_filter1d(np.interp(ss, s, V), SMOOTH / step, mode="nearest")
    ls = np.round(np.interp(ss, s, lab)).astype(int)
    return Xs, np.degrees(Vs / rho_ref), ls


class Strand(BS.Body):
    """One of the two bodies; side +1 is the left one, -1 its mirror image."""

    def __init__(self, front_polys, rear_polys, side=1, step=0.1):
        X, TH, lab = path_xtheta()
        TH = side * TH
        nb = 720
        thb = (np.arange(nb) + 0.5) / nb * 2 * np.pi - np.pi
        hf, hr = hull_radius(front_polys, thb), hull_radius(rear_polys, thb)
        th = np.radians(TH)
        thw = np.angle(np.exp(1j * th))
        wr = 1 - BS.smoothstep(BS.STEP_X - 5.0, BS.STEP_X + 15.0, X)
        rs = np.interp(thw, thb, hf, period=2 * np.pi) * (1 - wr) + np.interp(thw, thb, hr, period=2 * np.pi) * wr
        # arc length (provisional radius) for the taper
        C0 = np.c_[X, (rs + 10) * np.sin(th), (rs + 10) * np.cos(th)]
        s0 = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C0, axis=0), axis=1))]
        L0 = s0[-1]
        r = R_TIP + (R_MID - R_TIP) * (1 - (s0 / L0) ** TAPER_P)
        r = r - (R_MID - R_NECK) * (1 - BS.smoothstep(0.0, NECK_LEN, s0))
        r = r + NECK_FLARE[0] * (1 - BS.smoothstep(0.0, NECK_FLARE[1], s0))
        s_neck = s0[np.flatnonzero(lab == 0)].max() if (lab == 0).any() else 0.0
        q0 = 1 - (1 - Q_BODY) * BS.smoothstep(s_neck - 20.0, s_neck + 40.0, s0)
        # crossings with the other body: where this one passes the top or the bottom
        cross = np.flatnonzero(np.diff(np.floor(TH / 180.0)) != 0)
        cross = [i for i in cross if lab[i] == 1]
        lift = np.zeros(len(X))
        self.crossings = []
        for n, i in enumerate(sorted(cross, key=lambda i: X[i])):
            over = (n % 2 == 0) == (side > 0)          # left body over at the 1st and 3rd, right at the 2nd
            self.crossings.append((round(float(X[i]), 1), "top" if np.cos(th[i]) > 0 else "bottom", over))
            # the upper body rides up, the lower one sinks into the handguard (its belly is cut off),
            # so neither has to bend much
            amp = LIFT * 2 * q0[i] * r[i] * (0.55 if over else -0.45)
            lift += amp * np.exp(-0.5 * ((s0 - s0[i]) / 30.0) ** 2)
        rho = rs + (1 - EMBED) * q0 * r + lift
        C = np.c_[X, rho * np.sin(th), rho * np.cos(th)]
        tgt = HEAD_TARGET * np.array([1, np.sign(np.sin(th[lab == 0]).mean()), 1])
        w = BS.smoothstep(FADE_N[0], tgt[0], X)
        C = C * (1 - w[:, None]) + tgt[None] * w[:, None]
        seg = np.linalg.norm(np.diff(C, axis=0), axis=1)
        sc = np.r_[0, np.cumsum(seg)]
        self.s = np.arange(0, sc[-1], step)
        self.C = np.c_[[np.interp(self.s, sc, C[:, k]) for k in range(3)]].T
        self.C = ndi.gaussian_filter1d(self.C, 4.0 / step, axis=0, mode="nearest")
        self.r = np.interp(self.s, sc, r)
        self.q = np.interp(self.s, sc, q0)
        self.lab = np.round(np.interp(self.s, sc, lab)).astype(int)
        self.T, self.N, self.B = BS.frames(self.C)
        self.tree = BS.cKDTree(self.C)
        self.L = self.s[-1]
        self.side = side
        self.scale_n, self.scale_row, self.scale_depth, self.keel_h = 18, 5.0, 1.0, 0.4
        ds = np.gradient(self.s)
        self.phase = np.cumsum(ds * R_MID / np.maximum(self.r, 2.0))
        self.scale_fade = (1.2, 2.6)
        self.depth_r = 6.0

    def sdf(self, P, far=1e3):
        """Distance to the body: an ellipse in section (r across, q * r high). The head end is
        open (the head covers it); the tail end is the rounded tip."""
        d, i = self.tree.query(P, distance_upper_bound=self.r.max() + 4.0, workers=-1)
        out = np.full(len(P), far, np.float32)
        ok = np.isfinite(d)
        if not ok.any():
            return out
        i = i[ok]; Q = P[ok]
        D = Q - self.C[i]
        tcomp = (D * self.T[i]).sum(1)
        Dn = D - tcomp[:, None] * self.T[i]
        rad = np.linalg.norm(Dn, axis=1)
        s = self.s[i] + tcomp
        r = np.interp(s, self.s, self.r)
        q = np.interp(np.clip(s, 0, self.L), self.s, self.q)
        a = -(Dn * self.N[i]).sum(1)            # outward (away from the bore)
        v = np.arctan2((Dn * self.B[i]).sum(1), (Dn * self.N[i]).sum(1))
        b2 = np.maximum(rad ** 2 - a ** 2, 0) + np.where(s > self.L, s - self.L, 0) ** 2
        k0 = np.sqrt(b2 + (a / q) ** 2) / r
        k1 = np.sqrt(b2 + (a / q ** 2) ** 2) / r ** 2
        base = k0 * (k0 - 1) / np.maximum(k1, 1e-6)
        base = np.where(s < 0, np.maximum(base, -s), base)
        out[ok] = base + self.scales(s, v, r)
        return out


class Twin:
    """Both bodies together."""

    def __init__(self, front_polys, rear_polys):
        self.strands = [Strand(front_polys, rear_polys, 1), Strand(front_polys, rear_polys, -1)]
        self.crossings = self.strands[0].crossings

    def sdf(self, P):
        return np.minimum(self.strands[0].sdf(P), self.strands[1].sdf(P))


# ---- the head as a distance field ----
def smin(a, b, k):
    return BS.smin(a, b, k)


def smax(a, b, k):
    return BS.smax(a, b, k)


def head_sdf_grid(V, F, d_env_fn):
    g = HEAD_GRID; h = g["h"]
    xs = np.arange(g["x"][0], g["x"][1], h); ys = np.arange(g["y"][0], g["y"][1], h); zs = np.arange(g["z"][0], g["z"][1], h)
    grid = dict(x0=xs[0], y0=ys[0], z0=zs[0], h=h, nx=len(xs), ny=len(ys), nz=len(zs))
    tri = V[F]
    sel = (tri[:, :, 0].max(1) >= xs[0] - 1) & (tri[:, :, 0].min(1) <= xs[-1] + 1)
    occ = rasterize(V, F[sel], grid)
    if occ.max() <= 0:
        occ = rasterize(V, F[sel], grid, flip=True)
    X3 = xs[:, None, None]; Y3 = ys[None, :, None]; Z3 = zs[None, None, :]
    r3 = np.hypot(Y3, Z3)
    # not head: Meshy's handguard, rail and front sight behind the muzzle end, and its muzzle device
    behind = X3 < HG.X_END + 0.5
    occ = np.where(behind & (d_env_fn(Y3, Z3) < FM.GAP_TOP), 0.0, occ)
    occ = np.where((X3 > HG.X_END - 1) & (r3 < BS.PASSAGE_R), 0.0, occ)
    inside = occ > 0.5
    # keep only the head (largest piece) and what is attached to it
    lab, n = ndi.label(inside)
    if n > 1:
        sizes = ndi.sum(inside, lab, range(1, n + 1))
        inside = lab == (1 + int(np.argmax(sizes)))
    d = (ndi.distance_transform_edt(~inside) - ndi.distance_transform_edt(inside)) * h
    d = d + np.where(inside, 0.5, -0.5) * h
    return d.astype(np.float32), (xs[0], ys[0], zs[0], h)


def polycapsule(P, pts, radii):
    return np.minimum.reduce([BS.capsule(P, pts[i], pts[i + 1], radii[i], radii[i + 1]) for i in range(len(pts) - 1)])


def head_field(P, dgrid, gmeta):
    """Signed distance of the finished head at points P."""
    x0, y0, z0, h = gmeta
    c = np.vstack([(P[:, 0] - x0) / h, (P[:, 1] - y0) / h, (P[:, 2] - z0) / h])
    d = ndi.map_coordinates(dgrid, c, order=1, mode="nearest").astype(np.float64)
    X, Y, Z = P.T
    # rounded back of the head (a dome, not a flat cut)
    x_back = 372.0 + 0.028 * (Y ** 2 + (Z - 10.0) ** 2)
    d = smax(d, x_back - X, 6.0)
    # no fangs on the lower jaw
    d = smax(d, -FM.BS.ellipsoid(P, *LOW_FANG_HOLLOW), 2.0)
    # nose: narrow the snout gently toward a rounded tip (not flat, not needle-sharp)
    wedge = np.abs(Y) - 0.9 * (NOSE_TIP[0] + 6.0 - X)
    d = np.where(X > 425.0, smax(d, wedge, 4.0), d)
    d = smax(d, X - NOSE_TIP[0] - 0.12 * ((Y - NOSE_TIP[1]) ** 2 + (Z - NOSE_TIP[2]) ** 2), 3.0)
    d = smin(d, FM.BS.ellipsoid(P, *NOSE), 3.0)
    # Meshy's fang stubs out, the new fangs in their place: one smooth backward curve each,
    # tapering to a point, kept outside the barrel passage
    Pm = P.copy(); Pm[:, 1] = np.abs(Pm[:, 1])
    d = smax(d, -FM.BS.ellipsoid(P, *PALATE), 1.5)
    t = np.linspace(0, 1, 25)[:, None]
    p0, p1, p2 = (np.array(p) for p in FANG)
    pts = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2
    radii = FANG_TIP_R + (FANG_ROOT_R - FANG_TIP_R) * (1 - t[:, 0]) ** 1.3
    d = smin(d, polycapsule(Pm, pts, radii), 1.5)
    return d


# ---- voxel stage ----
def build(V, F, front_polys, rear_polys, x_range=(HG.X_FACE, 474.0), slab=24.0):
    body = Twin(front_polys, rear_polys)
    print("crossings (X, where, left body on top):", body.crossings)
    y0, y1, z0, z1 = -62.0, 62.0, -62.0, 66.0
    ys = y0 + np.arange(int((y1 - y0) / H) + 1) * H
    zs = z0 + np.arange(int((z1 - z0) / H) + 1) * H
    Yg, Zg = np.meshgrid(ys, zs, indexing="ij")

    def env_dist(polys, Yq, Zq):
        res = 0.1
        yy = np.arange(-30, 30, res); zz = np.arange(-40, 40, res)
        YY, ZZ = np.meshgrid(yy, zz, indexing="ij")
        inside = np.zeros(YY.shape, bool)
        for p in polys:
            inside |= contains_xy(p, YY, ZZ)
        dd = np.where(inside, -ndi.distance_transform_edt(inside), ndi.distance_transform_edt(~inside)) * res
        Yb, Zb = np.broadcast_arrays(Yq, Zq)
        c = np.vstack([((Yb - yy[0]) / res).ravel(), ((Zb - zz[0]) / res).ravel()])
        return ndi.map_coordinates(dd, c, order=1, mode="nearest").reshape(Yb.shape)
    d_env_front = lambda Yq, Zq: env_dist(front_polys, Yq, Zq)
    t0 = time.time()
    dgrid, gmeta = head_sdf_grid(V, F, d_env_front)
    print(f"  head distance field {dgrid.shape} {time.time() - t0:.0f}s", flush=True)
    xs_all = x_range[0] + np.arange(int((x_range[1] - x_range[0]) / H) + 1) * H
    halo = int(np.ceil(FM.CLEAN_T / H)) + 3
    nsl = int(slab / H)
    fields = []
    cut_count = {}
    for a in range(0, len(xs_all), nsl):
        lo = max(0, a - halo); hi = min(len(xs_all), a + nsl + 1 + halo)
        xs = xs_all[lo:hi]
        X3 = xs[:, None, None]
        P = np.stack(np.broadcast_arrays(X3, Yg[None], Zg[None]), -1).reshape(-1, 3)
        r = np.hypot(P[:, 1], P[:, 2])
        d = np.full(len(P), 1e3, np.float32)
        near = r > 15.0
        d[near] = body.sdf(P[near])
        hz = (P[:, 0] > HEAD_GRID["x"][0] + 1) & (P[:, 0] < HEAD_GRID["x"][1] - 1)
        if hz.any():
            dh = head_field(P[hz], dgrid, gmeta)
            d[hz] = smin(d[hz].astype(np.float64), dh, HEAD_BLEND)
        field = np.clip(0.5 - d / H, 0, 1).reshape(len(xs), len(ys), len(zs)).astype(np.float32)
        Y3 = Yg[None]; Z3 = Zg[None]
        for nm, m in (("sight", (X3 > SIGHT_X[0]) & (X3 < SIGHT_X[1]) & (np.abs(Y3) < SIGHT_YZ[0]) & (Z3 > SIGHT_YZ[1])),
                      ("bipod", (X3 > BIPOD_X[0]) & (X3 < BIPOD_X[1]) & (np.abs(Y3) < BIPOD_YZ[0]) & (Z3 < BIPOD_YZ[1])),
                      ("clamp", (X3 < 50.0) & (Z3 < -14.0) & (np.abs(Y3) < 16.5)),
                      ("rear face", X3 < HG.X_FACE + 3.0)):
            hit = np.count_nonzero(field[np.broadcast_to(m, field.shape)] > 0.5)
            cut_count[nm] = cut_count.get(nm, 0) + hit
        field[np.broadcast_to((X3 > SIGHT_X[0]) & (X3 < SIGHT_X[1]) & (np.abs(Y3) < SIGHT_YZ[0]) & (Z3 > SIGHT_YZ[1]), field.shape)] = 0
        field[np.broadcast_to((X3 > BIPOD_X[0]) & (X3 < BIPOD_X[1]) & (np.abs(Y3) < BIPOD_YZ[0]) & (Z3 < BIPOD_YZ[1]), field.shape)] = 0
        field[np.broadcast_to((X3 < 50.0) & (Z3 < -14.0) & (np.abs(Y3) < 16.5), field.shape)] = 0
        field[np.broadcast_to(X3 < HG.X_FACE + 3.0, field.shape)] = 0
        solid = field > 0.5
        kept = ndi.binary_opening(solid, structure=FM.ball(FM.CLEAN_T / 2))
        field = np.where(solid & ~kept, 0.0, field).astype(np.float32)
        fields.append(field[a - lo: a - lo + min(nsl, len(xs_all) - a)])
        print(f"  voxel slab X {xs_all[a]:.0f}  {time.time() - t0:.0f}s", flush=True)
    print("  snake cut by the keep-out zones (mm3, should be 0):", {k: round(v * H ** 3, 1) for k, v in cut_count.items()})
    vol = np.concatenate(fields, axis=0)
    lab, n = ndi.label(vol > 0.5, structure=np.ones((3, 3, 3)))
    if n > 1:
        sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1)) * H ** 3
        small = sizes < 0.2 * sizes.max()
        print(f"  removed {int(small.sum())} loose bits, {sizes[small].sum():.1f} mm3")
        vol = np.where(np.isin(lab, 1 + np.flatnonzero(small)), 0.0, vol).astype(np.float32)
    return vol, (xs_all[0], ys[0], zs[0]), body


# ---- joint, alignment tabs and side bolts ----
JOINT_GAP = 0.3            # gap between the two pieces' faces at the joint
TAB_W, TAB_H, TAB_L = 4.5, 5.0, 5.0    # alignment tab: across, radial, sticking out of the front piece
TAB_CLEAR = 0.2            # per side, tab to its pocket
TAB_WALL = 2.0             # material kept around every pocket
BOLT_HEAD_D = 9.6          # counterbore for an M5 socket head cap screw (head 8.5 mm)
BOLT_HEAD_H = 5.0
BOLT_CLEAR_D = 5.5
BOLT_LENGTHS = (12, 16, 20, 25, 30, 35)
BOLT_TIP_IN = 0.2          # the screw tip ends this far outside the bore, inside the 1.85 mm side wall (free float)
BOLT_SLOT_W = 6.0          # keymod narrow slot width


def side_slot_ends(base_tm):
    """(rear end, front end) X of every side keymod hole (same on both sides)."""
    yv = HG.FLAT_SIDE - 0.9
    sec = base_tm.section(plane_origin=[0, yv, 0], plane_normal=[0, 1, 0])
    P, _ = sec.to_2D(to_2D=np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, -yv], [0, 0, 0, 1]], float))
    ends = []
    for p in P.polygons_full:
        for r in p.interiors:
            x, z = np.asarray(r.xy)
            if abs(z.mean()) < 1.0 and 15.0 < x.max() - x.min() < 20.0 and 9.0 < z.max() - z.min() < 11.0:
                ends.append((round(float(x.min()), 2), round(float(x.max()), 2)))
    return sorted(ends)


def ray_solid(tm, origin, direction, t_max=80.0):
    """Solid intervals [t0, t1] of a watertight mesh along a ray."""
    loc, _, _ = tm.ray.intersects_location([origin], [direction], multiple_hits=True)
    t = np.sort((loc - origin) @ direction) if len(loc) else np.array([])
    t = t[(t > 0) & (t < t_max)]
    t = t[np.r_[True, np.diff(t) > 1e-4]] if len(t) else t
    return [(t[i], t[i + 1]) for i in range(0, len(t) - 1, 2)]


def box(c, ex, ey, ez):
    return Manifold.cube((ex, ey, ez), True).translate(tuple(c))


def joint_planes(body, xj):
    """Where the joint cuts each body: centre point and the cut plane's normal. The plane is
    turned halfway between square-to-the-body (no thin feather edges) and square-to-the-bore
    (the pieces slide together along the bore)."""
    out = []
    for st in body.strands:
        idx = np.flatnonzero((st.lab == 1) & (np.abs(st.C[:, 0] - xj) < 0.3))
        i = idx[len(idx) // 2]
        t = st.T[i] if st.T[i, 0] > 0 else -st.T[i]
        n = t + np.array([1.0, 0, 0]); n /= np.linalg.norm(n)
        out.append({"strand": "left" if st.side > 0 else "right", "p": st.C[i].copy(), "n": n, "r": float(st.r[i])})
    return out


def split_joint(snake, planes):
    balls = [Manifold.sphere(pl["r"] + 3.5, 96).translate(tuple(pl["p"])) for pl in planes]
    cut = snake
    for b in balls:
        cut = cut - b
    rest = sorted(cut.decompose(), key=lambda m: -m.volume())
    print("  joint: pieces after cutting out the two joint balls:", [round(m.volume()) for m in rest[:4]])
    rear = min(rest[:2], key=lambda m: m.bounding_box()[0]); front = max(rest[:2], key=lambda m: m.bounding_box()[0])
    for pl, b in zip(planes, balls):
        local = snake ^ b
        p, n = pl["p"], pl["n"]
        rear = rear + local.trim_by_plane(tuple(-n), float(-(n @ p)) + JOINT_GAP / 2)
        front = front + local.trim_by_plane(tuple(n), float(n @ p) + JOINT_GAP / 2)
    return rear, front


def tab_bar(c_yz, theta, x0, x1, w, h, grow=0.0):
    """Rectangular bar along X; its cross-section is centred at c_yz, w across (tangential)
    and h radial at angle theta (deg)."""
    b = box(((x0 + x1) / 2, 0, 0), x1 - x0 + 2 * grow, w + 2 * grow, h + 2 * grow).rotate((-theta, 0, 0))
    return b.translate((0, c_yz[0], c_yz[1]))


def tab_geometry(pl, d_rad, s_tan):
    """Tab bar on the face of one joint: centred d_rad outward and s_tan across from the
    strand centre (in the Y-Z plane), running along X from TAB_L behind the face to 6 mm in front."""
    p, n = pl["p"], pl["n"]
    theta = np.degrees(np.arctan2(p[1], p[2]))
    er = np.array([np.sin(np.radians(theta)), np.cos(np.radians(theta))])
    et = np.array([er[1], -er[0]])
    c = p[1:] + er * d_rad + et * s_tan
    # X of the face at the bar centre line
    xf = (n @ p - n[1] * c[0] - n[2] * c[1]) / n[0]
    return c, theta, xf


def place_tabs(rear, front, planes):
    """Two tabs on each joint face (strand A over the top, strand B under the bottom), where
    both pieces have TAB_WALL of material all round the tab and its pocket."""
    picks = []
    for pl in planes:
        lo = pl["p"] - 40; hi = pl["p"] + 40
        crop = Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
        rc, fc = rear ^ crop, front ^ crop
        miss = {}
        for s_tan in np.arange(-12.0, 12.5, 1.0):
            for d_rad in (-2.0, 0.0, 2.0, 4.0):
                c, th, xf = tab_geometry(pl, d_rad, s_tan)
                pocket = tab_bar(c, th, xf - TAB_L - 0.6 - TAB_WALL, xf - 0.5, TAB_W, TAB_H, TAB_CLEAR + TAB_WALL)
                pocket = pocket.trim_by_plane(tuple(-pl["n"]), float(-(pl["n"] @ pl["p"])) + JOINT_GAP / 2 + 0.3)
                root = tab_bar(c, th, xf + 0.5, xf + 6.0, TAB_W, TAB_H, TAB_WALL)
                root = root.trim_by_plane(tuple(pl["n"]), float(pl["n"] @ pl["p"]) + JOINT_GAP / 2 + 0.3)
                miss[(s_tan, d_rad)] = (pocket - rc).volume() + (root - fc).volume()
        best = None
        for (s1, d1), m1 in miss.items():
            for (s2, d2), m2 in miss.items():
                if s2 - s1 < TAB_W + 2 * TAB_CLEAR + TAB_WALL + 0.5:
                    continue
                score = m1 + m2 + 0.01 * abs(s1 + s2) + 0.01 * abs(d1 - d2)
                if best is None or score < best[0]:
                    best = (score, (s1, d1), (s2, d2))
        print(f"  tabs on the {pl['strand']} body: (across, out) {best[1]} and {best[2]}, material missing {best[0]:.2f} mm3")
        if best[0] > 12.0:     # a few mm3 is scale texture
            raise SystemExit(f"no room for the tabs on the {pl['strand']} body")
        for s_tan, d_rad in best[1:]:
            c, th, xf = tab_geometry(pl, d_rad, s_tan)
            picks.append({"strand": pl["strand"],
                          "y": round(float(c[0]), 2), "z": round(float(c[1]), 2), "theta": round(float(th), 1),
                          "face_x": round(float(xf), 2)})
    return picks


def add_tabs(rear, front, tabs):
    for t in tabs:
        c = (t["y"], t["z"]); th = t["theta"]; xf = t["face_x"]
        x_tip = xf - TAB_L
        # the leading 1.2 mm tapers by 0.6 mm a side, so the tab finds its pocket
        bar = tab_bar(c, th, x_tip + 1.2, xf + 6.0, TAB_W, TAB_H)
        tip = Manifold.batch_hull([tab_bar(c, th, x_tip, x_tip + 0.01, TAB_W - 1.2, TAB_H - 1.2),
                                   tab_bar(c, th, x_tip + 1.19, x_tip + 1.2, TAB_W, TAB_H)])
        front = front + bar + tip
        rear = rear - tab_bar(c, th, x_tip - 0.6, xf + 2.0, TAB_W, TAB_H, TAB_CLEAR)
    return rear, front


def place_bolts(piece, slot_ends, x_range, name, bear):
    """Two M5 screws, one from the left and one from the right at the same X (the snake is
    mirror-symmetric), each through a body into a side keymod hole, both the same length.
    bear="front": the screw sits at the front end of the hole's narrow slot (the piece cannot
    move forward); bear="rear": at the rear end of its round part (the piece cannot move back)."""
    tm = HG.to_trimesh(piece)
    y_tip = HG.R_BORE + BOLT_TIP_IN
    best = None
    for x_rear, x_front in slot_ends:
        xe = x_front if bear == "front" else x_rear
        xb = x_front - BOLT_SLOT_W / 2 + 0.25 if bear == "front" else x_rear + 2.5 + 0.2
        if not (x_range[0] < xb < x_range[1]):
            continue
        surf = {}
        for side in (1, -1):
            o = np.array([xb, 0.0, 0.0]); d = np.array([0, side, 0.0])
            # material all around the screw line: check the line and four lines around it
            ivs = []
            for dx, dz in ((0, 0), (4.8, 0), (-4.8, 0), (0, 4.8), (0, -4.8)):
                iv = ray_solid(tm, o + [dx, 0, dz], d)
                iv = [q for q in iv if q[0] < HG.FLAT_SIDE + 2.0]
                ivs.append(iv[0][1] if iv else 0.0)
            surf[side] = (ivs[0], min(ivs))
        print(f"    {name} slot X {xe}: snake surface left {surf[1][0]:.1f} right {surf[-1][0]:.1f}, "
              f"thinnest around {min(surf[1][1], surf[-1][1]):.1f}")
        for L in BOLT_LENGTHS:
            y_f = y_tip + L                        # under the head = top of the insert
            if y_f - BS.LOCK_INSERT_L < HG.FLAT_SIDE + CLEAR_MIN:
                continue
            if any(y_out < y_f + 1.0 or y_min < y_f - 0.5 for y_out, y_min in surf.values()):
                continue
            y_out = min(surf[1][0], surf[-1][0])
            score = (y_out - y_f >= BOLT_HEAD_H - 1.0, -abs(y_out - y_f - BOLT_HEAD_H), L)
            if best is None or score > best[0]:
                best = (score, xb, L, y_f, surf, xe)
    if best is None:
        raise SystemExit(f"{name}: no side keymod slot with enough snake over it on both sides")
    _, xb, L, y_f, surf, xe = best
    return [{"side": "left" if side > 0 else "right", "x": round(xb, 2), "bears_on": f"{bear} end of the keymod hole", "hole_end_x": xe,
             "screw": f"M5x{L} socket head cap screw", "insert_top_y": round(side * y_f, 2),
             "surface_y": round(side * surf[side][0], 2)} for side in (1, -1)]


CLEAR_MIN = 1.5


def add_bolt_holes(piece, bolts):
    for b in bolts:
        s = 1 if b["side"] == "left" else -1
        x = b["x"]; y_f = abs(b["insert_top_y"])
        cyl = lambda r, y0, y1: HG.cyl_y(r, x, 0.0, y0, y1) if s > 0 else HG.cyl_y(r, x, 0.0, -y1, -y0)
        piece = piece - cyl(BOLT_HEAD_D / 2, y_f, 90.0)                       # head
        piece = piece - cyl(BS.LOCK_INSERT_D / 2, y_f - BS.LOCK_INSERT_L, y_f + 0.1)   # heat-set insert
        piece = piece - cyl(BOLT_CLEAR_D / 2, HG.FLAT_SIDE - 1.0, y_f)        # screw
    return piece


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meshy_stl", nargs="?", default=os.path.join(HERE, "..", "work", "meshy", "snake_hg", "stl.stl"))
    ap.add_argument("--res", type=float, default=0.25)
    ap.add_argument("--cache", default=None, help="reuse / store the voxel snake mesh (.npz)")
    ap.add_argument("--outdir", default=os.path.join(HERE, ".."))
    ap.add_argument("--tolerance", type=float, default=0.02)
    a = ap.parse_args()
    global H
    H = FM.H = a.res
    t0 = time.time()
    front_polys, rear_polys = FM.profile_polys()
    if a.cache and os.path.exists(a.cache):
        z = np.load(a.cache)
        snake_tm = trimesh.Trimesh(z["v"], z["f"], process=False)
        body = Twin(front_polys, rear_polys)
    else:
        src = trimesh.load(a.meshy_stl); src.merge_vertices()
        V = FM.transform(np.asarray(src.vertices, float)); F = np.asarray(src.faces)
        thc, delta, _, _ = FM.radial_correction(V, F, front_polys)
        V = FM.apply_radial(V, thc, delta)
        vol, origin, body = build(V, F, front_polys, rear_polys)
        snake_tm = FM.mesh_field(vol, origin)
        if a.cache:
            np.savez(a.cache, v=snake_tm.vertices.astype(np.float32), f=snake_tm.faces.astype(np.int32))
    print("voxel snake:", len(snake_tm.faces), "faces, watertight", snake_tm.is_watertight, f"{time.time() - t0:.0f}s")
    snake = BS.to_manifold(snake_tm) - BS.handguard_envelope()
    snake = snake + HG.cyl_x(FM.THROAT[2], FM.THROAT[0], FM.THROAT[1])     # stop ring inside the head
    snake = snake - HG.cyl_x(BS.PASSAGE_R, HG.X_END - 0.5, 540.0)          # barrel passage, all the way out
    if a.tolerance > 0:
        snake = snake.simplify(a.tolerance)
    base = HG.build(json.load(open(os.path.join(HERE, "..", "data", "hole_templates.json"))))
    # the joint: strand A cut over the top, strand B under the bottom
    xj = X_SPLIT
    planes = joint_planes(body, xj)
    rear, front = split_joint(snake, planes)
    pieces = {"rear": rear, "front": front}
    for name in pieces:
        parts = sorted(pieces[name].decompose(), key=lambda p: -p.volume())
        dropped = [round(p.volume(), 2) for p in parts[1:]]
        print(f"  {name}: {len(parts)} part(s), dropped {dropped[:8]}")
        pieces[name] = parts[0]
    tabs = place_tabs(pieces["rear"], pieces["front"], planes)
    print("tabs:", tabs)
    pieces["rear"], pieces["front"] = add_tabs(pieces["rear"], pieces["front"], tabs)
    ends = side_slot_ends(HG.to_trimesh(base))
    print("side keymod slot front ends:", ends)
    # the rear piece's screws stop it moving back, the front piece's stop it moving forward; the
    # rear piece cannot move forward past the front piece, nor the head back past the handguard end
    bolts = {"rear": place_bolts(pieces["rear"], ends, (BS.STEP_X + 8, xj - TAB_L - 12), "rear", "rear"),
             "front": place_bolts(pieces["front"], ends, (xj + 12, SIGHT_X[1]), "front", "front")}
    print("bolts:", json.dumps(bolts, indent=1))
    for name in pieces:
        pieces[name] = add_bolt_holes(pieces[name], bolts[name])
    json.dump({"joint_x": xj, "joint_planes": [{"strand": pl["strand"], "point": pl["p"].round(2).tolist(),
                                                  "normal": pl["n"].round(4).tolist()} for pl in planes], "tabs": tabs, "tab_size_mm": [TAB_W, TAB_H, TAB_L], "bolts": bolts},
              open(os.path.join(HERE, "..", "data", "snake_lock.json"), "w"), indent=1)
    for name, piece in pieces.items():
        tm, slivers = FM.strip_slivers(HG.to_trimesh(piece))
        if not tm.is_watertight:
            trimesh.repair.fill_holes(tm)
        print(f"snake {name}: faces {len(tm.faces)}, watertight {tm.is_watertight}, "
              f"volume {tm.volume / 1000:.1f} cm3, size {(tm.bounds[1] - tm.bounds[0]).round(1).tolist()}")
        tm.export(os.path.join(a.outdir, f"snake_{name}.3mf"))
    both = pieces["rear"] + pieces["front"]
    HG.to_trimesh(base + both).export(os.path.join(HERE, "..", "work", "assembled_preview.stl"))
    print("overlap between handguard and snake (mm3, must be 0):", round((base ^ both).volume(), 4))
    print("overlap between the two pieces (mm3, must be 0):", round((pieces["rear"] ^ pieces["front"]).volume(), 4))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
