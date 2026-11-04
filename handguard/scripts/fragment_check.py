"""Find parts of a print that hang on by a thread: voxelize, erode away everything thinner
than BRIDGE mm (two nozzle widths), and label what is left. Any component other than the
main body is a fragment that only a hair-thin bridge connects, and it would print loose."""
import sys

import numpy as np
import trimesh
from scipy import ndimage as ndi

from thin_check import H, ball, rasterize  # noqa: F401


def fragments(path, bridge=0.8, min_vol=0.5, slab=40.0):
    m = trimesh.load(path, force="mesh")
    V, F = np.asarray(m.vertices, float), np.asarray(m.faces)
    lo, hi = m.bounds[0] - 2 * H, m.bounds[1] + 2 * H
    ny, nz = int((hi[1] - lo[1]) / H) + 1, int((hi[2] - lo[2]) / H) + 1
    nx = int((hi[0] - lo[0]) / H) + 1
    occ = np.zeros((nx, ny, nz), bool)
    tri_lo = V[F][:, :, 0].min(1); tri_hi = V[F][:, :, 0].max(1)
    st = int(slab / H)
    for a in range(0, nx, st):
        b = min(nx, a + st)
        x0 = lo[0] + a * H
        sel = (tri_hi >= x0 - H) & (tri_lo <= lo[0] + b * H + H)
        occ[a:b] = rasterize(V, F[sel], dict(x0=x0, y0=lo[1], z0=lo[2], h=H, nx=b - a, ny=ny, nz=nz)) > 0.5
    core = ndi.binary_erosion(occ, structure=ball(bridge / 2))
    lab, n = ndi.label(core, structure=np.ones((3, 3, 3)))
    if n == 0:
        return []
    sizes = ndi.sum(core, lab, range(1, n + 1)) * H ** 3
    main = int(np.argmax(sizes)) + 1
    out = []
    objs = ndi.find_objects(lab)
    for i in np.argsort(-sizes):
        if i + 1 == main or sizes[i] < min_vol:
            continue
        s = objs[i]
        idx = np.argwhere(lab[s] == i + 1) + np.array([sl.start for sl in s])
        p = lo + idx * H
        out.append((round(float(sizes[i]), 2), p.mean(0).round(1).tolist(), (p.max(0) - p.min(0) + H).round(1).tolist()))
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        r = fragments(p)
        print(p, len(r), "fragments joined by bridges under 0.8 mm")
        for o in r[:40]:
            print("  core mm3", o[0], "centre", o[1], "size", o[2])
