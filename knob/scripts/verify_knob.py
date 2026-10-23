"""Compare the knob model with the aligned scan (both in the measurement frame).

Usage: python verify_knob.py knob_scanframe.stl work/scan_aligned.ply --outdir verification
Writes deviation statistics (verification.json) and figures.
"""
import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
import trimesh
from scipy.spatial import cKDTree

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402


def plane_segments(mesh, n, d):
    """Line segments where the triangles of a (possibly open) mesh cross the plane n.x = d."""
    T = mesh.vertices[mesh.faces]
    s = T @ n - d
    T, s = T[(s.min(1) < 0) & (s.max(1) > 0)], s[(s.min(1) < 0) & (s.max(1) > 0)]
    pts, hit = [], []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        t = s[:, a] / (s[:, a] - s[:, b] + 1e-30)
        pts.append(T[:, a] + t[:, None] * (T[:, b] - T[:, a]))
        hit.append(s[:, a] * s[:, b] < 0)
    pts, hit = np.stack(pts, 1), np.stack(hit, 1)
    ok = hit.sum(1) == 2
    order = np.argsort(~hit[ok], axis=1, kind="stable")[:, :2]
    return np.take_along_axis(pts[ok], order[:, :, None], 1)


def signed_dist(mesh, pts, chunk=10_000):
    """Distance from points to a mesh, positive outside (sign from the nearest face normal)."""
    out = []
    for i in range(0, len(pts), chunk):
        q = pts[i:i + chunk]
        c, d, tri = trimesh.proximity.closest_point(mesh, q)
        s = np.sign(np.einsum("ij,ij->i", q - c, mesh.face_normals[tri]))
        out.append(d * np.where(s < 0, -1, 1))
    return np.concatenate(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("scan")
    ap.add_argument("--outdir", default="verification")
    ap.add_argument("--n", type=int, default=150_000)
    a = ap.parse_args()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    model = trimesh.load(a.model, process=False)
    scan = trimesh.load(a.scan, process=False)

    rng = np.random.default_rng(0)
    pts, _ = trimesh.sample.sample_surface(scan, a.n, seed=0)
    # keep scan points within the knob's envelope (drops stray background bits)
    r = np.hypot(pts[:, 0], pts[:, 1])
    keep = (r < 30.5) & (pts[:, 2] > -31) & (pts[:, 2] < 21.5)
    pts = pts[keep]
    sd = signed_dist(model, pts)
    d = np.abs(sd)

    # model to scan: distance to the nearest scan vertex (scan vertices are ~0.1 mm apart)
    mpts, _ = trimesh.sample.sample_surface(model, 150_000, seed=1)
    dm = cKDTree(scan.vertices).query(mpts)[0]

    def stats(v):
        v = np.abs(v)
        return {k: round(float(x), 3) for k, x in
                zip(("mean", "median", "p90", "p95", "p99", "max"),
                    (v.mean(), np.median(v), *np.percentile(v, [90, 95, 99]), v.max()))}

    res = {"scan_to_model": stats(d), "model_to_scan": stats(dm),
           "scan_points": int(len(pts)),
           "share_of_scan_within_0.2mm": round(float((d < 0.2).mean()), 4),
           "share_of_scan_within_0.5mm": round(float((d < 0.5).mean()), 4)}
    (out / "verification.json").write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=2))

    # deviation maps: scan points colored by signed distance, three views
    fig, ax = plt.subplots(1, 3, figsize=(21, 7.5))
    sel = rng.choice(len(pts), min(150_000, len(pts)), replace=False)
    p, s = pts[sel], sd[sel]
    for a_, (i, j, k, title) in zip(ax, [(0, 1, 2, "from the back (looking into the cup)"),
                                         (0, 2, 1, "side, along the bar"),
                                         (1, 2, 0, "side, across the bar")]):
        o = np.argsort(p[:, k])
        sc = a_.scatter(p[o, i], p[o, j], c=s[o], s=0.3, cmap="coolwarm", vmin=-0.5, vmax=0.5)
        a_.set_aspect("equal")
        a_.set_title(title)
    fig.colorbar(sc, ax=ax, shrink=0.8, label="scan minus model (mm), + = scan outside model")
    plt.savefig(out / "deviation_map.png", dpi=80, bbox_inches="tight")

    # cross sections: model (red) over scan (black)
    fig, ax = plt.subplots(1, 3, figsize=(24, 9))
    for a_, (normal, origin, h, v, title) in zip(ax, [
            ((0, 1, 0), (0, 0.01, 0), 0, 2, "section y=0 (along the bar)"),
            ((1, 0, 0), (0.01, 0, 0), 1, 2, "section x=0 (across the bar)"),
            ((0, 0, 1), (0, 0, -15), 0, 1, "section z=-15 (through the bar)")]):
        for mesh, col, lw in ((scan, "k", 0.6), (model, "r", 0.9)):
            seg = plane_segments(mesh, np.array(normal, float), np.dot(normal, origin))
            a_.add_collection(LineCollection(seg[:, :, [h, v]], colors=col, linewidths=lw))
        a_.autoscale()
        a_.set_aspect("equal")
        a_.grid(alpha=0.3)
        a_.set_title(title + "  (black: scan, red: model)")
    plt.savefig(out / "cross_sections.png", dpi=70, bbox_inches="tight")


if __name__ == "__main__":
    main()
