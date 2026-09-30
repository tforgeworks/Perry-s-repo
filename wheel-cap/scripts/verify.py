"""Compare the built cap against the aligned scan.

Reports two-way surface deviation (mean, 95th/99th percentile, max), bounding box
extents, diameters, height, volume, watertightness and front-face flatness, and
writes a Markdown summary, a JSON file and preview images.

Usage: python verify.py wheel_cap_CAP5372.stl work/scan_aligned.stl --outdir verification
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from scipy.spatial import cKDTree


def surface_distance(points, mesh, tree, face_of_sample, k=12):
    """Exact distance from points to mesh, using nearby dense samples to pick candidate faces."""
    _, idx = tree.query(points, k=k)
    cand = face_of_sample[idx]  # (n, k)
    best = np.full(len(points), np.inf)
    for j in range(k):
        tri = mesh.triangles[cand[:, j]]
        cp = trimesh.triangles.closest_point(tri, points)
        best = np.minimum(best, np.linalg.norm(cp - points, axis=1))
    return best


def dense_samples(mesh, n, seed):
    return trimesh.sample.sample_surface(mesh, n, seed=seed)


def stats(d):
    return dict(mean=float(d.mean()), p95=float(np.percentile(d, 95)),
                p99=float(np.percentile(d, 99)), max=float(d.max()))


def dims(m):
    v = m.vertices
    r = np.hypot(v[:, 0], v[:, 1])
    return dict(extents=[float(x) for x in m.extents], max_diameter=float(2 * r.max()),
                height=float(np.ptp(v[:, 2])), volume=float(m.volume), faces=int(len(m.faces)),
                watertight=bool(m.is_watertight))


def top_surface(m, R, step=0.5):
    """Height of the first surface hit by vertical rays from above, on a grid inside radius R."""
    g = np.arange(-R, R + step / 2, step)
    X, Y = np.meshgrid(g, g)
    keep = np.hypot(X, Y) < R
    orig = np.column_stack([X[keep], Y[keep], np.full(keep.sum(), m.bounds[1][2] + 5)])
    locs, ray_idx, _ = m.ray.intersects_location(orig, np.tile([0, 0, -1.0], (len(orig), 1)))
    top = np.full(len(orig), -np.inf)
    np.maximum.at(top, ray_idx, locs[:, 2])
    return top[np.isfinite(top)]


def section(m, normal, origin=(0, 0, 0)):
    s = m.section(plane_origin=origin, plane_normal=normal)
    if s is None:
        return []
    return [s.vertices[e.points] for e in s.entities]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("scan")
    ap.add_argument("--outdir", default="verification")
    ap.add_argument("--n", type=int, default=300_000)
    ap.add_argument("--face-radius", type=float, default=0.0,
                    help="radius of the flat front face for the flatness check (0 = auto)")
    args = ap.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    model = trimesh.load(args.model, force="mesh")
    scan = trimesh.load(args.scan, force="mesh")

    res = dict(model=dims(model), scan=dims(scan))

    ps, fs = dense_samples(scan, 3_000_000, 1)
    pm, fm = dense_samples(model, 3_000_000, 2)
    ts, tm = cKDTree(ps), cKDTree(pm)
    qm, _ = trimesh.sample.sample_surface(model, args.n, seed=4)
    qs, _ = trimesh.sample.sample_surface(scan, args.n, seed=5)
    d_m2s = surface_distance(qm, scan, ts, fs)
    d_s2m = surface_distance(qs, model, tm, fm)
    res["deviation_model_to_scan"] = stats(d_m2s)
    res["deviation_scan_to_model"] = stats(d_s2m)
    res["hausdorff"] = float(max(d_m2s.max(), d_s2m.max()))

    # front face flatness: the top surface near the center
    R = args.face_radius or 0.25 * res["model"]["max_diameter"] / 2
    tops = {}
    for name, m in (("model", model), ("scan", scan)):
        t = top_surface(m, R)
        tops[name] = dict(radius=float(R), z_median=float(np.median(t)),
                          z_std=float(t.std()), z_range=float(np.ptp(t)))
    res["front_face"] = tops
    (out / "verification.json").write_text(json.dumps(res, indent=2))

    # ---- figures
    fig, ax = plt.subplots(1, 2, figsize=(13, 6))
    for a, (pts, d, title) in zip(ax, ((qm, d_m2s, "model to scan, top view"),
                                        (qm, d_m2s, "model to scan, bottom view"))):
        order = np.argsort(pts[:, 2])
        if "bottom" in title:
            order = order[::-1]
        sc = a.scatter(pts[order, 0], pts[order, 1], c=d[order], s=0.3, cmap="viridis", vmin=0, vmax=0.5)
        a.set_aspect("equal")
        a.set_title(title)
        a.set_xlabel("x (mm)")
        a.set_ylabel("y (mm)")
    fig.colorbar(sc, ax=ax, label="deviation (mm)", shrink=0.8)
    fig.savefig(out / "deviation_map.png", dpi=110)
    plt.close(fig)

    fig, ax = plt.subplots(2, 1, figsize=(13, 8))
    for a, ang in zip(ax, (0.0, 30.0)):
        t = np.radians(ang)
        n = np.array([-np.sin(t), np.cos(t), 0.0])
        u = np.array([np.cos(t), np.sin(t), 0.0])
        for m, col, lab in ((scan, "tab:orange", "scan"), (model, "tab:blue", "model")):
            for i, seg in enumerate(section(m, n)):
                a.plot(seg @ u, seg[:, 2], color=col, lw=0.8, label=lab if i == 0 else None)
        a.set_aspect("equal")
        a.set_title(f"cross section through the axis at {ang:.0f} deg")
        a.legend(loc="upper right")
        a.set_xlabel("radial (mm)")
        a.set_ylabel("z (mm)")
    fig.tight_layout()
    fig.savefig(out / "cross_sections.png", dpi=110)
    plt.close(fig)

    md = ["| metric | model | scan |", "|---|---|---|"]
    for key, fmt in (("extents", "{:.2f} x {:.2f} x {:.2f} mm"), ("max_diameter", "{:.2f} mm"),
                     ("height", "{:.2f} mm"), ("volume", "{:,.0f} mm3"), ("faces", "{:,}"),
                     ("watertight", "{}")):
        vals = []
        for who in ("model", "scan"):
            v = res[who][key]
            vals.append(fmt.format(*v) if isinstance(v, list) else fmt.format(v))
        md.append(f"| {key.replace('_', ' ')} | {vals[0]} | {vals[1]} |")
    md += ["", "| surface deviation | mean | 95th pct | 99th pct | max |", "|---|---|---|---|---|"]
    for key, lab in (("deviation_model_to_scan", "model to scan"), ("deviation_scan_to_model", "scan to model")):
        s = res[key]
        md.append(f"| {lab} | {s['mean']:.3f} mm | {s['p95']:.3f} mm | {s['p99']:.3f} mm | {s['max']:.3f} mm |")
    ff = res["front_face"]
    md += ["", f"Front face (top surface within r < {R:.1f} mm): model height spread "
               f"{ff['model']['z_range']:.3f} mm (std {ff['model']['z_std']:.3f}), scan "
               f"{ff['scan']['z_range']:.3f} mm (std {ff['scan']['z_std']:.3f})."]
    (out / "verification.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
