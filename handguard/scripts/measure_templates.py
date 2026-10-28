"""Measure the outline of every hole type on the aligned scan.

The outer surface is unrolled into an (X, theta) map: a cell is "material" when an
outward-facing scan triangle lies there. Holes are the connected empty regions.
Repeated holes of one type are stacked on their centroids and averaged, and the
0.5 contour of the average becomes that type's outline (smoothed with a Fourier
low-pass). Output: data/hole_templates.json, outlines as (dX mm, dtheta deg).
"""
import argparse
import json

import numpy as np
from scipy import ndimage as ndi
from skimage import measure

DX, DTH = 0.2, 0.4  # map resolution: mm along X, degrees around


def material_map(T):
    C = T.mean(1)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    r = np.hypot(C[:, 1], C[:, 2])
    nr = (n[:, 1] * C[:, 1] + n[:, 2] * C[:, 2]) / r
    th = np.degrees(np.arctan2(C[:, 1], C[:, 2]))
    k = (nr > 0.5) & (r > 17.6)
    W = int(390 / DX) + 1; H = int(360 / DTH)
    M = np.zeros((H, W), bool)
    M[((th[k] + 180) / DTH).astype(int) % H, (C[k, 0] / DX).astype(int)] = True
    return M


def holes(M):
    mat = ndi.binary_opening(ndi.binary_closing(M, iterations=2), iterations=1)
    lab, _ = ndi.label(~mat, structure=np.ones((3, 3)))
    out = []
    for i, s in enumerate(ndi.find_objects(lab)):
        m = lab[s] == i + 1
        if m.sum() < 300:
            continue
        yy, xx = np.nonzero(m)
        yy = yy + s[0].start; xx = xx + s[1].start
        out.append(dict(yy=yy, xx=xx, area=len(yy), th=-180 + (yy.mean() + 0.5) * DTH, x=(xx.mean() + 0.5) * DX))
    return out


def average_outline(instances, mirror, tol=0.08):
    med = np.median([h["area"] for h in instances])
    use = [(h, mf) for h, mf in zip(instances, mirror) if abs(h["area"] - med) < tol * med]
    hx = int(14 / DX); ht = int(24 / DTH)
    acc = np.zeros((2 * ht + 1, 2 * hx + 1))
    for h, mf in use:
        ry = np.round(h["yy"] - h["yy"].mean()).astype(int)
        rx = np.round(h["xx"] - h["xx"].mean()).astype(int)
        if mf:
            ry = -ry
        ok = (abs(ry) <= ht) & (abs(rx) <= hx)
        acc[ry[ok] + ht, rx[ok] + hx] += 1
    acc /= len(use)
    c = max(measure.find_contours(acc, 0.5), key=len)
    return np.c_[(c[:, 1] - hx) * DX, (c[:, 0] - ht) * DTH], len(use)


def smooth(P, keep=24, n=160):
    P = np.vstack([P, P[:1]])
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = np.linspace(0, s[-1], n, endpoint=False)
    z = np.interp(t, s, P[:, 0]) + 1j * np.interp(t, s, P[:, 1])
    F = np.fft.fft(z); F[keep + 1:-keep] = 0
    z = np.fft.ifft(F)
    return np.c_[z.real, z.imag]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scan_tris", help="aligned scan triangles from align_scan.py")
    ap.add_argument("--out", default="../data/hole_templates.json")
    a = ap.parse_args()
    M = material_map(np.load(a.scan_tris).astype(np.float64))
    side = holes(M)
    bottom = holes(np.roll(M, M.shape[0] // 2, axis=0))  # theta=180 moved to the map centre
    pick = lambda hs, lo, hi, x0=0, x1=400: [h for h in hs if lo < h["th"] < hi and x0 < h["x"] < x1]
    rows = {
        "upper": (pick(side, 30, 50), pick(side, -50, -30), 39.15),
        "lower": (pick(side, 125, 140), pick(side, -140, -125), 133.42),
        "keymod": (pick(side, 85, 95, 0, 368), pick(side, -95, -85, 0, 368), 90.0),
        "front": (pick(side, 85, 95, 368, 390), [], 90.0),
        "bottomkey": (pick(bottom, -10, 10), [], 180.0),
    }
    out = {}
    for name, (pos, neg, thc) in rows.items():
        P, n = average_outline(pos + neg, [False] * len(pos) + [True] * len(neg))
        out[name] = {"theta_center_deg": thc, "instances": n,
                     "outline_dx_mm_dtheta_deg": np.round(smooth(P), 4).tolist()}
        print(f"{name:10s} {n:3d} instances, X centres {sorted(round(h['x'], 1) for h in pos)[:4]}...")
    json.dump(out, open(a.out, "w"))


if __name__ == "__main__":
    main()
