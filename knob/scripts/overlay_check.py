"""Lay the model over the aligned scan and list every place where they disagree.

Scan points farther than the threshold from the model surface, and model surface
farther than the threshold from any scan point, are grouped into connected clusters
and printed with their size, deviation and bounding box. The scan's background, the
black insert inside the bore and the unscanned front faces are left out.

Usage: python overlay_check.py work/knob_scanframe.stl work/scan_aligned.ply [threshold_mm]
"""
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.csgraph as cg
import trimesh
from scipy.spatial import cKDTree


def clusters(pts, val, label, link=0.5, top=15, min_pts=60):
    if len(pts) == 0:
        print(label, "none")
        return
    pairs = cKDTree(pts).query_pairs(link, output_type="ndarray")
    graph = sp.coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(pts),) * 2)
    _, lab = cg.connected_components(graph, directed=False)
    cnt = np.bincount(lab)
    print(f"{label}: {len(pts)} points in {len(cnt)} clusters; largest:")
    for k in np.argsort(-cnt)[:top]:
        if cnt[k] < min_pts:
            break
        c, v = pts[lab == k], val[lab == k]
        lo, hi = c.min(0), c.max(0)
        print(f"  n={cnt[k]:5d} dev med {np.median(v):+.2f} max {v[np.argmax(abs(v))]:+.2f}"
              f"  x {lo[0]:6.1f}..{hi[0]:6.1f}  y {lo[1]:6.1f}..{hi[1]:6.1f}  z {lo[2]:6.1f}..{hi[2]:6.1f}")


def main():
    model = trimesh.load(sys.argv[1], process=False)
    scan = trimesh.load(sys.argv[2], process=False)
    thr = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3

    pts, _ = trimesh.sample.sample_surface(scan, 700_000, seed=0)
    r = np.hypot(pts[:, 0], pts[:, 1])
    keep = (r < 29.5) & (pts[:, 2] > -30.2) & (pts[:, 2] < 21) & ~((r < 7.2) & (pts[:, 2] > -26.5))
    pts = pts[keep]
    sd = []
    for i in range(0, len(pts), 20_000):
        q = pts[i:i + 20_000]
        c, d, tri = trimesh.proximity.closest_point(model, q)
        sd.append(d * np.sign(np.einsum("ij,ij->i", q - c, model.face_normals[tri])))
    sd = np.concatenate(sd)
    clusters(pts[sd > thr], sd[sd > thr], "scan outside the model")
    clusters(pts[sd < -thr], sd[sd < -thr], "scan inside the model")

    mpts, _ = trimesh.sample.sample_surface(model, 300_000, seed=1)
    dm = cKDTree(scan.vertices).query(mpts)[0]
    far = (dm > thr) & (mpts[:, 2] > -29.0)   # the front faces were not scanned
    clusters(mpts[far], dm[far], "model surface with no scan nearby")


if __name__ == "__main__":
    main()
