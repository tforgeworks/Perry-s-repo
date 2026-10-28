"""Sculpt the viper that coils around the handguard and fuse it to the CAD body.

The snake is a signed distance field (SDF): a swept body along a centreline that
weaves under the handguard from side to side, keeled overlapping scales displaced
onto it, and a viper head with an open mouth at the muzzle end. The field is
meshed with marching cubes in slabs, then unioned with the handguard.

Keep-outs (the snake never enters them):
  * the Picatinny rail and the space above it, so the full rail stays usable
  * the bore, and a 31 mm passage through the head for the barrel and muzzle device
  * the rear clamp (cross bolts, centre screw, slit) and the receiver end
"""
import argparse
import json
import os
import time

import numpy as np
import trimesh
from manifold3d import Manifold, Mesh
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes

import build_handguard as HG

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ body path
R_SURF = 19.4      # where the belly rests (tube radius, a little into the flats)
EMBED = 0.35       # fraction of the body radius sunk into the handguard
R_BODY = 8.5       # body radius
WAVE_X0, WAVE_X1 = 60.0, 360.0
WAVE_LAMBDA = 100.0
WAVE_AMP = 115.0   # degrees either side of the bottom; peaks at 65 deg from top
TAIL_X0 = 8.0

# head (X of the handguard's muzzle end is HG.X_END = 387.4)
HEAD_BACK = 374.0  # first X the head may occupy (the last rail slot ends at 373.3)
PASSAGE_R = 15.5   # clear radius around the bore axis through the head (31 mm)

# scales
SCALE_N = 20             # scales around the body
SCALE_ROW = 2.7          # mm between scale rows along the body
SCALE_DEPTH = 0.55       # groove depth
KEEL_H = 0.25            # keel ridge height
HEAD_CELL = 3.0          # head scale size
HEAD_DEPTH = 0.45


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
    # tail along the +Y side of the rear tube, rising slightly toward the first coil
    x = np.arange(TAIL_X0, WAVE_X0, step)
    t = (x - TAIL_X0) / (WAVE_X0 - TAIL_X0)
    xs.append(x); ths.append(88 - 23 * smoothstep(0, 1, t)); extra.append(np.zeros_like(x))
    # coils: weave under the handguard between 65 deg right and 65 deg left of the top
    x = np.arange(WAVE_X0, WAVE_X1, step * 0.25)
    xs.append(x); ths.append(180 - WAVE_AMP * np.cos(2 * np.pi * (x - WAVE_X0) / WAVE_LAMBDA))
    extra.append(np.zeros_like(x))
    # neck: run forward along the right side and lift into the head's cheek
    x = np.arange(WAVE_X1, 393.0, step)
    t = (x - WAVE_X1) / (393.0 - WAVE_X1)
    xs.append(x); ths.append(65 - 5 * smoothstep(0, 1, t)); extra.append(4.0 * smoothstep(0.3, 1, t))
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
    r = np.where(s < tail, 1.0 + (R_BODY - 1.0) * smoothstep(0, 1, s / tail) ** 0.8, r)
    neck0 = L - 70.0
    r = np.where(s > neck0, R_BODY - 1.3 * smoothstep(neck0, L - 20, s), r)
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
        d, i = self.tree.query(P, distance_upper_bound=R_BODY + 4.0, workers=-1)
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
        L = SCALE_ROW
        W = 2 * np.pi / SCALE_N
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
        keel = KEEL_H * np.exp(-(dw_best / 0.12) ** 2) * smoothstep(0.0, 0.3, second - best)
        bump = SCALE_DEPTH * edge * ramp + keel
        # belly (facing the handguard) stays smooth; scale size fades with the tail
        dorsal = smoothstep(0.6, 1.3, np.abs(v))
        fade = smoothstep(2.0, 4.5, r)
        return (SCALE_DEPTH - bump) * dorsal * fade


# ------------------------------------------------------------------ head SDF
def ellipsoid(P, c, r, pitch_deg=0.0):
    Q = P - np.asarray(c)
    if pitch_deg:
        a = np.radians(pitch_deg)  # rotate about Y: +pitch lifts the front (+X) end
        x = Q[:, 0] * np.cos(a) + Q[:, 2] * np.sin(a)
        z = -Q[:, 0] * np.sin(a) + Q[:, 2] * np.cos(a)
        Q = np.c_[x, Q[:, 1], z]
    r = np.asarray(r, float)
    k0 = np.linalg.norm(Q / r, axis=1)
    k1 = np.linalg.norm(Q / (r * r), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def capsule(P, a, b, ra, rb):
    a = np.asarray(a, float); b = np.asarray(b, float)
    ba = b - a; pa = P - a
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[:, None] * ba, axis=1) - (ra + (rb - ra) * h)


def mirror_y(fn, P):
    Q = P.copy(); Q[:, 1] = np.abs(Q[:, 1])
    return fn(Q)


def head_parts(P):
    X = P[:, 0]
    # collar: elliptic sleeve over the last 13 mm of the handguard
    grow = 0.85 + 0.15 * smoothstep(HEAD_BACK, HEAD_BACK + 12.0, X)
    ell = np.sqrt((P[:, 1] / (25.0 * grow)) ** 2 + ((P[:, 2] - 6.0) / (31.0 * grow)) ** 2)
    collar = (ell - 1.0) * 25.0
    collar = smax(collar, HEAD_BACK + 0.5 - X, 1.0)
    collar = smax(collar, X - 400.0, 4.0)
    skull = ellipsoid(P, (402, 0, 24), (25, 23, 14.5))
    snout = ellipsoid(P, (425, 0, 26), (14, 14.5, 8.5), pitch_deg=10)
    cheeks = mirror_y(lambda Q: ellipsoid(Q, (397, 17, 2), (15, 9.5, 26)), P)
    jaw = ellipsoid(P, (411, 0, -24), (25, 18, 6.5), pitch_deg=-14)
    head = smin(collar, skull, 5.0)
    head = smin(head, snout, 4.0)
    head = smin(head, cheeks, 5.0)
    head = smin(head, jaw, 4.0)
    brows = mirror_y(lambda Q: ellipsoid(Q, (411, 13.5, 34), (10, 6, 3.6), pitch_deg=-8), P)
    head = smin(head, brows, 2.0)
    # mouth: wide gape, plus the barrel / muzzle device passage
    mouth = ellipsoid(P, (434, 0, 1.5), (33, 29, 18.5))
    passage = np.hypot(P[:, 1], P[:, 2]) - PASSAGE_R
    passage = np.where(X > HG.X_END - 0.5, passage, 1e3)
    hollow = smin(mouth, passage, 2.0)
    head = smax(head, -hollow, 1.5)
    # eye sockets and eyes with slit pupils
    sockets = mirror_y(lambda Q: ellipsoid(Q, (412, 16.5, 29.5), (5.4, 4.2, 5.0)), P)
    head = smax(head, -sockets, 0.8)
    eyes = mirror_y(lambda Q: np.linalg.norm(Q - np.array([412.5, 15.6, 29.5]), axis=1) - 4.3, P)
    pupils = mirror_y(lambda Q: ellipsoid(Q, (412.5, 19.9, 29.5), (0.55, 0.9, 2.9)), P)
    eyes = np.maximum(eyes, -pupils)
    nostrils = mirror_y(lambda Q: np.linalg.norm(Q - np.array([436.0, 5.0, 28.5]), axis=1) - 1.4, P)
    head = smax(head, -nostrils, 0.5)
    # fangs (stay outside the passage) and small teeth
    fangs = mirror_y(lambda Q: np.minimum(capsule(Q, (423.5, 12.6, 21.5), (427.5, 13.3, 14.5), 2.3, 1.4),
                                          capsule(Q, (427.5, 13.3, 14.5), (430.5, 13.6, 9.5), 1.4, 0.45)), P)
    lowfangs = mirror_y(lambda Q: capsule(Q, (421.0, 12.0, -24.0), (426.5, 13.4, -11.5), 2.0, 0.45), P)
    detail = np.minimum(fangs, lowfangs)
    return head, eyes, detail, hollow


def worley(P, cell):
    """Distance to the nearest and second-nearest jittered lattice point."""
    g = np.floor(P / cell).astype(np.int64)
    d1 = np.full(len(P), 1e9); d2 = np.full(len(P), 1e9)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = g + np.array([dx, dy, dz])
                h = (c[:, 0] * 73856093) ^ (c[:, 1] * 19349663) ^ (c[:, 2] * 83492791)
                h = (h * 2654435761) & 0xFFFFFFFF
                jit = np.c_[(h & 1023) / 1023.0, ((h >> 10) & 1023) / 1023.0, ((h >> 20) & 1023) / 1023.0]
                fp = (c + 0.15 + 0.7 * jit) * cell
                d = np.linalg.norm(P - fp, axis=1)
                d2 = np.where(d < d1, d1, np.minimum(d2, d))
                d1 = np.minimum(d1, d)
    return d1, d2


def head_sdf(P):
    head, eyes, detail, hollow = head_parts(P)
    d1, d2 = worley(P * np.array([0.8, 1.0, 1.0]), HEAD_CELL)
    groove = HEAD_DEPTH * (1 - smoothstep(0.0, 0.35 * HEAD_CELL, d2 - d1))
    smooth_zone = smoothstep(0.5, 3.0, hollow)          # no scales inside the mouth
    head = head + groove * smooth_zone
    return np.minimum(np.minimum(head, eyes), detail)


# ------------------------------------------------------------------ keep-outs
def keepout_sdf(P):
    """Positive outside the regions the snake must leave free; negative inside."""
    X, Y, Z = P.T
    k = []
    # rail and the space above it (accessories, clamps, optics), up to the head
    rail = np.maximum.reduce([np.abs(Y) - 17.5, 19.5 - Z, X - HEAD_BACK, HG.X_FACE - 2 - X])
    k.append(rail)
    # bore of the handguard
    k.append(np.where(X < HG.X_END, np.hypot(Y, Z) - (HG.R_BORE + 0.2), 1e3))
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


def mesh_snake(res, slab_mm=24.0):
    body = Body()
    x0, x1 = HG.X_FACE, 446.0
    y0, y1 = -40.0, 40.0
    z0, z1 = -40.0, 46.0
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
    m.merge_vertices(digits_vertex=5)
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    return m


def to_manifold(tm):
    return Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                         tri_verts=np.asarray(tm.faces, np.uint32)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=float, default=0.25)
    ap.add_argument("--tolerance", type=float, default=0.02, help="mesh simplification tolerance (mm)")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "handguard_snake.3mf"))
    ap.add_argument("--cache", default=None, help="reuse / store the raw snake mesh (.npz)")
    ap.add_argument("--split", type=float, default=209.4, help="X of the joint for the two-piece version (0 = none)")
    ap.add_argument("--outdir", default=os.path.join(HERE, ".."), help="where the two split pieces go")
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
    combined = base + to_manifold(sm)
    if a.tolerance > 0:
        combined = combined.simplify(a.tolerance)
    # drop any zero-volume crumbs left by the booleans
    parts = sorted(combined.decompose(), key=lambda p: -p.volume())
    dropped = [round(p.volume(), 4) for p in parts[1:]]
    combined = parts[0]
    out = HG.to_trimesh(combined)
    print("dropped crumbs (mm3)", dropped)
    print("combined faces", len(out.faces), "watertight", out.is_watertight,
          "volume cm3", round(out.volume / 1000, 2), "bounds", out.bounds.round(1).tolist())
    out.export(a.out)  # .3mf keeps the exact manifold topology and is a quarter of the STL size
    if a.split:
        for name, piece in split_with_pins(combined, a.split).items():
            tm = HG.to_trimesh(piece)
            print(name, "faces", len(tm.faces), "watertight", tm.is_watertight, "bounds", tm.bounds.round(1).tolist())
            tm.export(os.path.join(a.outdir, f"handguard_snake_{name}.3mf"))


PIN_D = 3.2      # holes for 3 mm dowel pins (or 3 mm rod)
PIN_DEPTH = 6.0  # each side of the joint


def split_with_pins(m, xc, n_pins=3, min_wall=3.0):
    """Cut at X=xc into rear and front pieces with matching dowel-pin holes."""
    from scipy import ndimage as ndi
    from shapely import contains_xy
    tm = HG.to_trimesh(m)
    sec = tm.section(plane_origin=[xc, 0, 0], plane_normal=[1, 0, 0])
    to2d = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -xc], [0, 0, 0, 1]], float)
    planar, _ = sec.to_2D(to_2D=to2d)
    res = 0.1
    ys = np.arange(-45, 45, res); zs = np.arange(-45, 50, res)
    Y, Z = np.meshgrid(ys, zs, indexing="ij")
    inside = np.zeros(Y.shape, bool)
    for poly in planar.polygons_full:
        inside |= contains_xy(poly, Y, Z)
    dist = ndi.distance_transform_edt(inside) * res
    cand = np.argwhere(dist >= PIN_D / 2 + min_wall - 1.6)
    pts = np.c_[ys[cand[:, 0]], zs[cand[:, 1]]]
    if len(pts) == 0:
        raise SystemExit(f"no room for pins at X={xc}")
    # keep only spots where the whole pin hole (both sides of the joint) is inside solid
    slab = m.trim_by_plane((1, 0, 0), xc - PIN_DEPTH - 2).trim_by_plane((-1, 0, 0), -(xc + PIN_DEPTH + 2))
    local = HG.to_trimesh(slab)
    rng = np.random.default_rng(0)
    pts = pts[rng.permutation(len(pts))[:600]]
    ang = np.linspace(0, 2 * np.pi, 12, endpoint=False)
    ring = np.c_[np.cos(ang), np.sin(ang)] * (PIN_D / 2 + 1.0)
    ok = []
    for p in pts:
        probe = [(xc + dx, p[0] + q[0], p[1] + q[1]) for dx in (-PIN_DEPTH - 1, -PIN_DEPTH / 2, PIN_DEPTH / 2, PIN_DEPTH + 1) for q in ring]
        ok.append(local.contains(np.array(probe)).all())
    pts = pts[np.array(ok)]
    if len(pts) == 0:
        raise SystemExit(f"no room for pins at X={xc}")
    # spread the pins out: farthest-point sampling
    chosen = [pts[0]]
    for _ in range(n_pins - 1):
        dmin = np.min([np.linalg.norm(pts - c, axis=1) for c in chosen], axis=0)
        if dmin.max() < PIN_D + 3:
            break
        chosen.append(pts[np.argmax(dmin)])
    print("pin centres (Y, Z):", np.round(chosen, 1).tolist())
    holes = [Manifold.cylinder(2 * PIN_DEPTH, PIN_D / 2, PIN_D / 2, 32)
             .transform(np.array([[0, 0, 1, xc - PIN_DEPTH], [1, 0, 0, y], [0, 1, 0, z]], float))
             for y, z in chosen]
    cut = m - Manifold.batch_boolean(holes, HG._union_op())
    rear = cut.trim_by_plane((-1, 0, 0), -xc)   # keeps X <= xc
    front = cut.trim_by_plane((1, 0, 0), xc)    # keeps X >= xc
    return {"rear": rear, "front": front}


if __name__ == "__main__":
    main()
