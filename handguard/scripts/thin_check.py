"""Find thin, breakable features in a printed part.

The part is voxelized (0.25 mm) in slabs along X. Everything a ball of diameter MIN_T
(2 mm = 5 nozzle widths) can pass through is removed (morphological opening); the connected
leftovers bigger than a few mm3 are the thin features. Shallow surface texture (scale ridges)
is too small in volume and drops out.
"""
import os
import sys

import numpy as np
import trimesh
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "wheel-cap", "scripts"))
from build_cap import rasterize  # noqa: E402

H = 0.25


def ball(r):
    n = int(np.ceil(r / H))
    g = np.mgrid[-n:n + 1, -n:n + 1, -n:n + 1] * H
    return (g ** 2).sum(0) <= r * r


def thin_features(path, min_t=2.0, min_vol=4.0, slab=40.0):
    m = trimesh.load(path, force="mesh")
    V, F = np.asarray(m.vertices, float), np.asarray(m.faces)
    lo, hi = m.bounds[0] - 2 * H, m.bounds[1] + 2 * H
    ny, nz = int((hi[1] - lo[1]) / H) + 1, int((hi[2] - lo[2]) / H) + 1
    halo = int(np.ceil(min_t / H)) + 2
    nx = int((hi[0] - lo[0]) / H) + 1
    st = int(slab / H)
    thin_all = []
    tri_lo = V[F][:, :, 0].min(1); tri_hi = V[F][:, :, 0].max(1)
    for a in range(0, nx, st):
        i0 = max(0, a - halo); i1 = min(nx, a + st + halo)
        x0 = lo[0] + i0 * H
        sel = (tri_hi >= x0 - H) & (tri_lo <= lo[0] + i1 * H + H)
        occ = rasterize(V, F[sel], dict(x0=x0, y0=lo[1], z0=lo[2], h=H, nx=i1 - i0, ny=ny, nz=nz)) > 0.5
        opened = ndi.binary_opening(occ, structure=ball(min_t / 2))
        thin = (occ & ~opened)[a - i0: a - i0 + min(st, nx - a)]
        thin_all.append(thin)
    thin = np.concatenate(thin_all, 0)
    lab, n = ndi.label(thin)
    if n == 0:
        return [], m
    sizes = ndi.sum(thin, lab, range(1, n + 1)) * H ** 3
    objs = ndi.find_objects(lab)
    out = []
    for i in np.argsort(-sizes):
        if sizes[i] < min_vol:
            break
        s = objs[i]
        idx = np.argwhere(lab[s] == i + 1) + np.array([sl.start for sl in s])
        pts = lo + idx * H
        out.append((round(float(sizes[i]), 1), pts.mean(0).round(1).tolist(), (pts.max(0) - pts.min(0)).round(1).tolist()))
    return out, m


if __name__ == "__main__":
    for p in sys.argv[1:]:
        res, m = thin_features(p)
        print(p, f"volume {m.volume / 1000:.1f} cm3, {len(res)} thin features (> 4 mm3, under 2 mm thick)")
        for o in res[:30]:
            print("  vol mm3", o[0], "centre", o[1], "extent", o[2])
