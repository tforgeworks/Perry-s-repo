"""Sculpt the removable viper that slides onto the handguard.

The snake is a signed distance field (SDF): a swept body along a centreline that
weaves under the handguard from side to side, keeled overlapping scales displaced
onto it, and a viper head with a gaping mouth at the muzzle end. The field is
meshed with marching cubes in slabs.

The snake is a separate part. Its inside is cut to the handguard's outer envelope
plus a running clearance, so it slides on from the muzzle end and wraps about 230
degrees around the handguard: it cannot lift off, and the flats and the rail stop it
from turning. It comes in two pieces that each fit a 256 mm bed:
  * rear piece (tail and first coils): stops against the step where the keymod
    flats start (X = 63), and is held there by the front piece
  * front piece (coils and head): the head's inner wall stops against the
    handguard's muzzle end, and an M5 set screw through the top of the head
    (heat-set insert) drops into the last rail slot to lock it

Keep-outs (the snake never enters them):
  * the Picatinny rail and the space above it, so the rail stays usable up to the head
  * a 31 mm passage through the head for the barrel and muzzle device
  * the rear clamp (cross bolts, centre screw, slit) and the receiver end
"""
import argparse
import json
import os
import time

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, Mesh
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes

import build_handguard as HG

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ body path
R_SURF = 19.4      # where the belly rests (tube radius, a little into the flats)
EMBED = 0.3        # fraction of the body radius below the handguard surface (cut off as the belly)
R_BODY = 9.0       # body radius
WAVE_X0, WAVE_X1 = 60.0, 360.0
WAVE_LAMBDA = 100.0
WAVE_AMP = 115.0   # degrees either side of the bottom; peaks at 65 deg from top
TAIL_X0 = 8.0

# fit to the handguard
CLEARANCE = 0.35   # running clearance between the snake and the handguard
STEP_X = HG.PANEL_X + 0.2  # the rear piece stops on the step where the keymod flats start

# head (X of the handguard's muzzle end is HG.X_END = 387.4)
HEAD_BACK = 365.0  # first X the head occupies; covers rail slot 37 (centre 370.7) only
PASSAGE_R = 15.5   # clear radius around the bore axis through the head (31 mm)
HINGE = (388.0, 6.0)          # corner of the gape (X, Z)
GAPE_UP = (444.0, 21.0)       # front of the palate
GAPE_DOWN = (440.0, -25.0)    # front of the lower jaw's top line
LOCK_X = HG.RAIL_SLOT_X0 + (HG.RAIL_SLOTS - 1) * HG.RAIL_PITCH  # set screw into the last rail slot
LOCK_SCREW_D = 5.3            # clearance for an M5 set screw
LOCK_INSERT_D = 6.4           # M5 heat-set insert hole
LOCK_INSERT_L = 6.0             # short M5 insert (M5 x 5.8)

# scales
SCALE_N = 16             # scales around the body
SCALE_ROW = 3.3          # mm between scale rows along the body
SCALE_DEPTH = 0.7        # groove depth
KEEL_H = 0.3             # keel ridge height
HEAD_CELL = 4.2          # head scale size
HEAD_DEPTH = 0.65


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


# ------------------------------------------------------------------ centreline
def centreline(step=0.1):
    """Dense samples of the body centreline from tail tip to the neck."""
    xs, ths, extra = [], [], []
    # tail along the left (+Y) side of the rear tube, rising slightly toward the first coil
    x = np.arange(TAIL_X0, WAVE_X0, step)
    t = (x - TAIL_X0) / (WAVE_X0 - TAIL_X0)
    xs.append(x); ths.append(88 - 23 * smoothstep(0, 1, t)); extra.append(np.zeros_like(x))
    # coils: weave under the handguard between 65 deg left and 65 deg right of the top
    x = np.arange(WAVE_X0, WAVE_X1, step * 0.25)
    xs.append(x); ths.append(180 - WAVE_AMP * np.cos(2 * np.pi * (x - WAVE_X0) / WAVE_LAMBDA))
    extra.append(np.zeros_like(x))
    # neck: run forward along the left side and lift into the back of the head
    x = np.arange(WAVE_X1, 392.0, step)
    t = (x - WAVE_X1) / (392.0 - WAVE_X1)
    xs.append(x); ths.append(65 - 10 * smoothstep(0, 1, t)); extra.append(5.0 * smoothstep(0.2, 1, t))
    x = np.concatenate(xs); th = np.radians(np.concatenate(ths)); lift = np.concatenate(extra)
    # resample uniformly in arc length
    s_raw = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.c_[x, 25 * np.sin(th), 25 * np.cos(th)], axis=0), axis=1))]
    s = np.arange(0, s_raw[-1], step)
    x = np.interp(s, s_raw, x); th = np.interp(s, s_raw, th); lift = np.interp(s, s_raw, lift)
    r = radius_profile(s)
    rho = R_SURF + (1 - EMBED) * r + lift
    C = np.c_[x, rho * np.sin(th), rho * np.cos(th)]
    return s, C, r


def radius_profile(s):
    L = s[-1] if np.ndim(s) else s
    r = np.full_like(s, R_BODY)
    tail = 150.0
    r = np.where(s < tail, 1.2 + (R_BODY - 1.2) * smoothstep(0, 1, s / tail) ** 0.8, r)
    neck0 = L - 70.0
    r = np.where(s > neck0, R_BODY - 1.5 * smoothstep(neck0, L - 20, s), r)
    return r


def frames(C):
    """Unit tangent, plus normal pointing at the bore axis (belly side)."""
    T = np.gradient(C, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    inward = np.c_[np.zeros(len(C)), -C[:, 1], -C[:, 2]]
    N = inward - T * (inward * T).sum(1, keepdims=True)
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    B = np.cross(T, N)
    return T, N, B


# ------------------------------------------------------------------ body SDF
class Body:
    def __init__(self):
        self.s, self.C, self.r = centreline()
        self.T, self.N, self.B = frames(self.C)
        self.tree = cKDTree(self.C)
        self.L = self.s[-1]

    def sdf(self, P, far=1e3):
        d, i = self.tree.query(P, distance_upper_bound=self.r.max() + 4.0, workers=-1)
        out = np.full(len(P), far, np.float32)
        ok = np.isfinite(d)
        if not ok.any():
            return out
        i = i[ok]; Q = P[ok]
        D = Q - self.C[i]
        # remove the tangential part (nearest sample, 0.1 mm spacing)
        tcomp = (D * self.T[i]).sum(1)
        Dn = D - tcomp[:, None] * self.T[i]
        rad = np.linalg.norm(Dn, axis=1)
        s = self.s[i] + tcomp
        r = np.interp(s, self.s, self.r)
        v = np.arctan2((Dn * self.B[i]).sum(1), (Dn * self.N[i]).sum(1))  # 0 = belly
        base = np.sqrt(rad**2 + np.where(s < 0, s, 0) ** 2 + np.where(s > self.L, s - self.L, 0) ** 2) - r
        out[ok] = base + self.scales(s, v, r)
        return out

    def scales(self, s, v, r):
        """Keeled, overlapping diamond scales (displacement, positive = groove)."""
        L = getattr(self, "scale_row", SCALE_ROW)
        W = 2 * np.pi / getattr(self, "scale_n", SCALE_N)
        depth = getattr(self, "scale_depth", SCALE_DEPTH)
        keel_h = getattr(self, "keel_h", KEEL_H)
        best = np.full(len(s), 9.0); second = np.full(len(s), 9.0)
        cu_best = np.zeros(len(s)); dw_best = np.zeros(len(s))
        i0 = np.floor(s / L)
        for di in (-1, 0, 1, 2):
            i = i0 + di
            off = 0.5 * (np.mod(i, 2))
            j = np.round(v / W - off)
            for dj in (-1, 0, 1):
                vc = (j + dj + off) * W
                du = (s - i * L) / L
                dw = np.angle(np.exp(1j * (v - vc))) / W
                m = np.abs(du) + np.abs(dw)
                better = m < best
                second = np.where(better, best, np.minimum(second, m))
                cu_best = np.where(better, du, cu_best)
                dw_best = np.where(better, dw, dw_best)
                best = np.where(better, m, best)
        edge = smoothstep(0.0, 0.35, second - best)            # 0 on the seams
        ramp = 0.55 + 0.45 * np.clip(0.5 - cu_best, 0, 1)      # free edge toward the tail
        keel = keel_h * np.exp(-(dw_best / 0.12) ** 2) * smoothstep(0.0, 0.3, second - best)
        bump = depth * edge * ramp + keel
        # belly (facing the handguard) stays smooth; scale size fades with the tail
        dorsal = smoothstep(0.6, 1.3, np.abs(v))
        fade = smoothstep(2.0, 4.5, r)
        return (depth - bump) * dorsal * fade


# ------------------------------------------------------------------ head SDF
def ellipsoid(P, c, r, yaw_deg=0.0):
    Q = P - np.asarray(c)
    if yaw_deg:
        a = np.radians(yaw_deg)  # rotate about Z
        x = Q[:, 0] * np.cos(a) + Q[:, 1] * np.sin(a)
        y = -Q[:, 0] * np.sin(a) + Q[:, 1] * np.cos(a)
        Q = np.c_[x, y, Q[:, 2]]
    r = np.asarray(r, float)
    k0 = np.linalg.norm(Q / r, axis=1)
    k1 = np.linalg.norm(Q / (r * r), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def capsule(P, a, b, ra, rb):
    a = np.asarray(a, float); b = np.asarray(b, float)
    ba = b - a; pa = P - a
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[:, None] * ba, axis=1) - (ra + (rb - ra) * h)


def polycapsule(P, pts, radii):
    return np.minimum.reduce([capsule(P, pts[i], pts[i + 1], radii[i], radii[i + 1]) for i in range(len(pts) - 1)])


def mirror_y(fn, P):
    Q = P.copy(); Q[:, 1] = np.abs(Q[:, 1])
    return fn(Q)


def loft(P, xs, w, c, h, n=2.5, k=3.0):
    """Superellipse cross-sections (half-width w, centre height c, half-height h)
    interpolated along X between xs[0] and xs[-1], with rounded end caps."""
    X = P[:, 0]
    W = np.interp(X, xs, w); Cz = np.interp(X, xs, c); H = np.interp(X, xs, h)
    q = (np.abs(P[:, 1] / W) ** n + np.abs((P[:, 2] - Cz) / H) ** n) ** (1.0 / n)
    d = (q - 1.0) * np.minimum(W, H)
    return smax(smax(d, xs[0] - X, k), X - xs[-1], k)


def gape_lines(X):
    """Z of the palate (upper) and of the lower jaw's top (lower) at X."""
    hx, hz = HINGE
    up = hz + (X - hx) * (GAPE_UP[1] - hz) / (GAPE_UP[0] - hx)
    lo = hz + (X - hx) * (GAPE_DOWN[1] - hz) / (GAPE_DOWN[0] - hx)
    return up, lo


def head_parts(P):
    X = P[:, 0]
    up, lo = gape_lines(X)
    # back of the head: wraps the handguard's muzzle end, widest at the jaw angles
    back = loft(P, [HEAD_BACK, 380, 392, 402], [22.0, 26.0, 29.0, 26.0], [9.5, 9.5, 9.5, 11.0],
                [31.0, 31.0, 30.0, 25.0], n=2.4, k=6.0)
    # upper head: flat-topped wedge from the jaw angles to a rounded snout
    upper = loft(P, [384, 400, 425, 440, 447], [28.0, 26.0, 18.0, 11.5, 6.5],
                 [24.0, 25.0, 25.5, 25.0, 24.5], [15.0, 13.5, 9.0, 6.5, 4.0], n=2.7, k=3.0)
    # lower jaw: drops from the hinge to a narrow chin
    lower = loft(P, [384, 400, 425, 441, 444], [25.0, 23.0, 14.0, 7.5, 4.5],
                 [-6.0, -11.0, -21.5, -28.5, -29.5], [9.0, 7.5, 5.5, 4.5, 3.5], n=2.6, k=2.5)
    head = smin(back, upper, 5.0)
    head = smin(head, lower, 4.0)
    # venom-gland bulges behind the jaw angles, and the brow plates over the eyes
    glands = mirror_y(lambda Q: ellipsoid(Q, (392, 25.5, 12), (12, 6, 11)), P)
    head = smin(head, glands, 4.0)
    brows = mirror_y(lambda Q: ellipsoid(Q, (412, 16.5, 36.0), (11.5, 5.2, 3.0), yaw_deg=12), P)
    head = smin(head, brows, 1.5)
    canthus = mirror_y(lambda Q: capsule(Q, (418, 15.0, 35.0), (442, 7.0, 30.5), 2.0, 1.2), P)
    head = smin(head, canthus, 2.0)
    # the gape: open between the palate line and the lower jaw line, ahead of the hinge
    mouth = smax(smax(HINGE[0] - X, P[:, 2] - up, 1.0), lo - P[:, 2], 1.0)
    passage = np.where(X > HG.X_END - 0.5, np.hypot(P[:, 1], P[:, 2]) - PASSAGE_R, 1e3)
    hollow = smin(mouth, passage, 3.0)
    head = smax(head, -hollow, 1.5)
    # eyes under the brows, with slit pupils; each eye overlaps the back of its socket so it stays attached
    sockets = mirror_y(lambda Q: np.linalg.norm(Q - np.array([411.0, 20.3, 31.0]), axis=1) - 4.6, P)
    head = smax(head, -sockets, 0.8)
    eyes = mirror_y(lambda Q: np.linalg.norm(Q - np.array([411.0, 19.4, 31.0]), axis=1) - 4.3, P)
    pupils = mirror_y(lambda Q: ellipsoid(Q, (411.0, 23.7, 31.0), (0.5, 0.8, 2.8)), P)
    eyes = np.maximum(eyes, -pupils)
    nostrils = mirror_y(lambda Q: np.linalg.norm(Q - np.array([443.5, 5.0, 27.5]), axis=1) - 1.4, P)
    head = smax(head, -nostrils, 0.5)
    # long curved fangs at the front of the upper jaw, short ones at the chin;
    # every tip stays outside the passage
    fangs = mirror_y(lambda Q: polycapsule(Q, [(434.5, 11.0, 22.0), (437.5, 12.4, 15.5), (440.0, 13.6, 8.6)],
                                           [2.3, 1.5, 0.45]), P)
    lowfangs = mirror_y(lambda Q: polycapsule(Q, [(430.0, 9.0, -22.5), (432.0, 10.8, -16.5), (433.5, 12.0, -12.0)],
                                              [1.9, 1.2, 0.45]), P)
    detail = np.minimum(fangs, lowfangs)
    return head, eyes, detail, hollow


def worley(P, cell):
    """Nearest / second-nearest distances to a jittered lattice, and the nearest point."""
    g = np.floor(P / cell).astype(np.int64)
    d1 = np.full(len(P), 1e9); d2 = np.full(len(P), 1e9); f1 = np.zeros_like(P)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = g + np.array([dx, dy, dz])
                h = (c[:, 0] * 73856093) ^ (c[:, 1] * 19349663) ^ (c[:, 2] * 83492791)
                h = (h * 2654435761) & 0xFFFFFFFF
                jit = np.c_[(h & 1023) / 1023.0, ((h >> 10) & 1023) / 1023.0, ((h >> 20) & 1023) / 1023.0]
                fp = (c + 0.15 + 0.7 * jit) * cell
                d = np.linalg.norm(P - fp, axis=1)
                closer = d < d1
                d2 = np.where(closer, d1, np.minimum(d2, d))
                f1 = np.where(closer[:, None], fp, f1)
                d1 = np.minimum(d1, d)
    return d1, d2, f1


def head_sdf(P):
    head, eyes, detail, hollow = head_parts(P)
    # shingled scales: seams between cells, each scale lifted at its rear (free) edge
    S = P * np.array([0.75, 1.0, 1.0])
    d1, d2, f1 = worley(S, HEAD_CELL)
    edge = smoothstep(0.0, 0.3 * HEAD_CELL, d2 - d1)
    lift = np.clip(0.5 - (S[:, 0] - f1[:, 0]) / HEAD_CELL, 0, 1)
    groove = HEAD_DEPTH * (1 - edge * (0.45 + 0.55 * lift))
    smooth_zone = smoothstep(0.5, 3.0, hollow)          # no scales inside the mouth
    head = head + groove * smooth_zone
    return np.minimum(np.minimum(head, eyes), detail)


# ------------------------------------------------------------------ keep-outs
def keepout_sdf(P):
    """Positive outside the regions the snake must leave free; negative inside."""
    X, Y, Z = P.T
    k = []
    # rail and the space above it (accessories, clamps, optics), up to the head
    k.append(np.maximum.reduce([np.abs(Y) - 17.5, 19.5 - Z, X - HEAD_BACK, HG.X_FACE - 2 - X]))
    # rear clamp: bottom block with the cross bolts, centre screw and slit
    k.append(np.maximum(X - 64.0, Z + 14.0))
    # receiver end
    k.append(X - (HG.X_FACE + 3.0))
    return np.minimum.reduce(k)


# ------------------------------------------------------------------ meshing
def snake_field(P, body):
    d = body.sdf(P)
    near_head = P[:, 0] > HEAD_BACK - 2
    if near_head.any():
        h = np.full(len(P), 1e3, np.float32)
        h[near_head] = head_sdf(P[near_head])
        d = smin(d, h, 3.0)
    return np.maximum(d, -keepout_sdf(P))


def mesh_snake(res, slab_mm=24.0, x_range=(HG.X_FACE, 450.0)):
    body = Body()
    x0, x1 = x_range
    y0, y1 = -42.0, 42.0
    z0, z1 = -42.0, 46.0
    ys = np.arange(y0, y1 + res, res); zs = np.arange(z0, z1 + res, res)
    xs_all = np.arange(x0, x1 + res, res)
    nslab = int(round(slab_mm / res))
    verts, faces, nv = [], [], 0
    t0 = time.time()
    for a in range(0, len(xs_all) - 1, nslab):
        xs = xs_all[a:a + nslab + 1]
        G = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), -1).reshape(-1, 3)
        F = snake_field(G, body).reshape(len(xs), len(ys), len(zs)).astype(np.float32)
        # close the volume at the outer box faces
        pad = np.pad(F, 1, constant_values=1.0)
        if a > 0:
            pad = pad[1:]  # shared plane with the previous slab: no cap there
        if a + nslab < len(xs_all) - 1:
            pad = pad[:-1]
        if (pad < 0).any():
            v, f, _, _ = marching_cubes(pad, 0.0, spacing=(res, res, res))
            off = np.array([xs[0] - (res if a == 0 else 0), y0 - res, z0 - res])
            verts.append(v + off); faces.append(f + nv); nv += len(v)
        print(f"  slab x={xs[0]:.0f}..{xs[-1]:.0f}  {time.time() - t0:.0f}s", flush=True)
    m = trimesh.Trimesh(np.vstack(verts), np.vstack(faces), process=False)
    # slabs share their boundary planes; merge those vertices, and close the rare crack
    # where marching cubes resolved an ambiguous face differently on the two sides
    m.merge_vertices(digits_vertex=4)
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    trimesh.repair.fill_holes(m)
    return m


def to_manifold(tm):
    m = Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                      tri_verts=np.asarray(tm.faces, np.uint32)))
    if m.is_empty():
        raise SystemExit(f"mesh is not a valid manifold: {m.status()}")
    return m


# ------------------------------------------------------------------ fit to the handguard
def handguard_envelope():
    """The space the handguard sweeps as the snake slides on from the muzzle end,
    grown by the running clearance: its outer profile with every hole, slot and
    flat recess filled."""
    circle = CrossSection.circle(HG.R_OUT, HG.SEG)
    flats = CrossSection.square((2 * HG.FLAT_SIDE, 2 * HG.R_OUT + 2)).translate((-HG.FLAT_SIDE, -HG.FLAT_BOT))
    rail = HG.rail_profile()
    grow = lambda cs: cs.offset(CLEARANCE, JoinType.Round, circular_segments=HG.SEG)
    front = HG.extrude_x(grow((circle ^ flats) + rail), -10.0, HG.X_END + CLEARANCE)
    rear = HG.extrude_x(grow(circle + rail), -10.0, STEP_X + CLEARANCE)
    return front + rear


def head_top_z(x, y=0.0):
    zs = np.arange(30.0, 46.0, 0.02)
    P = np.c_[np.full_like(zs, x), np.full_like(zs, y), zs]
    d = head_sdf(P)
    inside = np.flatnonzero(d < 0)
    return zs[inside.max()] if len(inside) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=float, default=0.25)
    ap.add_argument("--tolerance", type=float, default=0.02, help="mesh simplification tolerance (mm)")
    ap.add_argument("--cache", default=None, help="reuse / store the raw snake mesh (.npz)")
    ap.add_argument("--split", type=float, default=209.4, help="X of the joint between the two snake pieces")
    ap.add_argument("--outdir", default=os.path.join(HERE, ".."))
    a = ap.parse_args()
    templates = json.load(open(os.path.join(HERE, "..", "data", "hole_templates.json")))
    base = HG.build(templates)
    if a.cache and os.path.exists(a.cache):
        z = np.load(a.cache)
        sm = trimesh.Trimesh(z["v"], z["f"], process=False)
    else:
        print("meshing snake...")
        sm = mesh_snake(a.res)
        if a.cache:
            np.savez(a.cache, v=sm.vertices.astype(np.float32), f=sm.faces.astype(np.int32))
    print("snake faces", len(sm.faces), "watertight", sm.is_watertight)
    snake = to_manifold(sm) - handguard_envelope()
    # lock screw: insert hole from the head's top surface down LOCK_INSERT_L, clearance below
    top = head_top_z(LOCK_X)
    print("head top above the lock slot: Z =", round(top, 2), " (rail top", HG.RAIL_TOP, ")")
    if top - LOCK_INSERT_L < HG.RAIL_TOP + CLEARANCE + 0.8:
        raise SystemExit("not enough material above the rail for the lock-screw insert")
    insert = Manifold.cylinder(LOCK_INSERT_L + 5, LOCK_INSERT_D / 2, LOCK_INSERT_D / 2, 48) \
        .translate((LOCK_X, 0, top - LOCK_INSERT_L))
    clear = Manifold.cylinder(top - HG.RAIL_TOP + 2, LOCK_SCREW_D / 2, LOCK_SCREW_D / 2, 48) \
        .translate((LOCK_X, 0, HG.RAIL_TOP - 1))
    snake = snake - insert - clear
    if a.tolerance > 0:
        snake = snake.simplify(a.tolerance)
    pieces = {
        "rear": snake.trim_by_plane((-1, 0, 0), -a.split),   # keeps X <= split
        "front": snake.trim_by_plane((1, 0, 0), a.split),    # keeps X >= split
    }
    for name, piece in pieces.items():
        parts = sorted(piece.decompose(), key=lambda p: -p.volume())
        dropped = [round(p.volume(), 3) for p in parts[1:]]
        tm = HG.to_trimesh(parts[0])
        print(f"snake {name}: faces {len(tm.faces)}, watertight {tm.is_watertight}, "
              f"volume {tm.volume / 1000:.1f} cm3, bounds {tm.bounds.round(1).tolist()}, dropped {dropped}")
        tm.export(os.path.join(a.outdir, f"snake_{name}.3mf"))
        pieces[name] = parts[0]
    # assembled preview: handguard + both snake pieces in place
    preview = HG.to_trimesh(base + pieces["rear"] + pieces["front"])
    preview.export(os.path.join(a.outdir, "work", "assembled_preview.stl"))
    gap = (base ^ (pieces["rear"] + pieces["front"])).volume()
    print("overlap between handguard and snake (mm3, must be 0):", round(gap, 4))


if __name__ == "__main__":
    main()
