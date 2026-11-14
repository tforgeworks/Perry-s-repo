"""Compare the rebuilt handguard with the aligned scan.

Distances are measured from scan points to the model surface. Points on the
accessories bolted to the original (front sight, bottom accessory rail, screw
heads) are excluded because they are not part of the handguard.
"""
import argparse
import json

import numpy as np
import trimesh
from scipy.spatial import cKDTree


def accessory_mask(P):
    X, Y, Z = P.T
    sight = (X > 305) & (X < 372) & (Z > 26)
    bottom_rail = (X > 252) & (X < 376) & (Z < -18.0) & (np.abs(Y) < 14)
    heads = (X > 14) & (X < 48) & (Y < -11.9) & (Z < -14)
    return sight | bottom_rail | heads


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("scan_tris")  # aligned scan triangles, .npy (n,3,3)
    ap.add_argument("--n", type=int, default=400000)
    ap.add_argument("--out", default="verification.json")
    ap.add_argument("--fig", default=None, help="write the unrolled deviation map here")
    a = ap.parse_args()
    m = trimesh.load(a.model)
    T = np.load(a.scan_tris)
    rng = np.random.default_rng(0)
    idx = rng.choice(len(T), size=min(a.n, len(T)), replace=False)
    P = T[idx].mean(1).astype(np.float64)
    P = P[~accessory_mask(P)]
    # dense model samples -> KD tree (fast nearest distance, 0.05 mm sampling error)
    S, _ = trimesh.sample.sample_surface_even(m, 6_000_000)
    d, _ = cKDTree(S).query(P, workers=-1)
    res = {
        "points": int(len(P)),
        "mean_mm": float(d.mean()), "median_mm": float(np.median(d)),
        "p90_mm": float(np.percentile(d, 90)), "p95_mm": float(np.percentile(d, 95)),
        "p99_mm": float(np.percentile(d, 99)), "max_mm": float(d.max()),
    }
    res["regions"] = region_stats(P, d)
    print(json.dumps(res, indent=1))
    json.dump(res, open(a.out, "w"), indent=1)
    if a.fig:
        deviation_figure(P, d, a.fig)


def region_stats(P, d):
    X, Y, Z = P.T
    r = np.hypot(Y, Z)
    regions = {
        "rail top": (Z > 30.5) & (np.abs(Y) < 7) & (X > 3) & (X < 305),
        "rail dovetail flanks": (Z > 25) & (Z < 30) & (np.abs(Y) > 8.5) & (np.abs(Y) < 11.5) & (X < 305),
        "rear tube OD": (X > 5) & (X < 60) & (r > 19) & (r < 20.5) & (Z > -12),
        "barrel-nut bore": (X > 3) & (X < 45) & (r < 18) & (r > 16.5),
        "clamp block": (X > 3) & (X < 60) & (Z < -19),
        "slotted section outer skin": (X > 65) & (X < 380) & (r > 17.8) & (r < 20.2),
    }
    return {k: {"points": int(m.sum()), "median_mm": round(float(np.median(d[m])), 3),
                "p95_mm": round(float(np.percentile(d[m], 95)), 3)} for k, m in regions.items()}


def deviation_figure(P, d, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    th = np.degrees(np.arctan2(P[:, 1], P[:, 2]))
    fig, ax = plt.subplots(2, 1, figsize=(16, 9), gridspec_kw={"height_ratios": [3, 1]})
    o = np.argsort(d)
    sc = ax[0].scatter(P[o, 0], th[o], c=d[o], s=0.2, cmap="turbo", vmin=0, vmax=1.0, rasterized=True)
    plt.colorbar(sc, ax=ax[0]).set_label("scan to model distance (mm)")
    ax[0].set_xlabel("X along the bore axis (mm), receiver end at 0")
    ax[0].set_ylabel("angle around the bore (deg), 0 = rail, +90 = left side")
    ax[0].set_title("Rebuilt handguard vs. 3D scan, unrolled (accessories bolted to the original are excluded)")
    ax[1].hist(d, bins=150, range=(0, 1.5), color="#4a6fa5")
    ax[1].set_xlabel("distance (mm)"); ax[1].set_ylabel("scan points")
    ax[1].axvline(np.median(d), color="k", lw=1)
    ax[1].text(np.median(d) + 0.02, ax[1].get_ylim()[1] * 0.8, f"median {np.median(d):.2f} mm")
    plt.tight_layout(); plt.savefig(path, dpi=80)


if __name__ == "__main__":
    main()
