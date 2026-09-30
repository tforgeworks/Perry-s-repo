"""Symmetry diagnostics for the aligned scan.

Draws the top-view thickness map, its difference from the D6 average, and the clip
ring unwrapped around the axis (angle vs height), so features that differ between
the six sectors stand out.

Usage: python diagnose.py work/scan_aligned.stl --out verification/symmetry.png
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from scipy import ndimage

from build_cap import make_grid, rasterize


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scan")
    ap.add_argument("--out", default="verification/symmetry.png")
    ap.add_argument("--h", type=float, default=0.25)
    args = ap.parse_args()
    m = trimesh.load(args.scan, force="mesh")
    V = m.vertices
    h = args.h
    g = make_grid((V.min(0), V.max(0)), h, pad=4)
    occ = rasterize(V, m.faces, g)
    T = occ.sum(axis=2) * h
    n = g["nx"]
    c = g["x0"] + np.arange(n) * h
    X, Y = np.meshgrid(c, c, indexing="ij")

    def samp(img, qx, qy):
        return ndimage.map_coordinates(img, [(qx - g["x0"]) / h, (qy - g["y0"]) / h], order=1)

    avg = np.zeros_like(T)
    for mir in (1, -1):
        for k in range(6):
            t = k * np.pi / 3
            qx = np.cos(t) * X - np.sin(t) * Y
            qy = mir * (np.sin(t) * X + np.cos(t) * Y)
            avg += samp(T, qx, qy)
    avg /= 12

    # unwrapped ring: occupancy summed over a radial band, as angle x height
    rmax = np.hypot(V[:, 0], V[:, 1]).max()
    ang = np.radians(np.arange(0, 360, 0.25))
    rs = np.arange(0.62 * rmax, 0.9 * rmax, h)
    zs = np.arange(occ.shape[2])
    A, Rr, Z = np.meshgrid(ang, rs, zs, indexing="ij")
    qx, qy = Rr * np.cos(A), Rr * np.sin(A)
    ring = ndimage.map_coordinates(occ, [(qx - g["x0"]) / h, (qy - g["y0"]) / h, Z], order=1).sum(axis=1) * h

    fig = plt.figure(figsize=(16, 13))
    ax1 = fig.add_subplot(2, 2, 1)
    im = ax1.imshow(T.T, origin="lower", extent=[c[0], c[-1], c[0], c[-1]], cmap="gray")
    ax1.set_title("scan thickness along the axis (mm)")
    fig.colorbar(im, ax=ax1, shrink=0.8)
    ax2 = fig.add_subplot(2, 2, 2)
    im = ax2.imshow((T - avg).T, origin="lower", extent=[c[0], c[-1], c[0], c[-1]], cmap="RdBu_r", vmin=-2, vmax=2)
    ax2.set_title("scan minus D6 average (mm)")
    fig.colorbar(im, ax=ax2, shrink=0.8)
    ax3 = fig.add_subplot(2, 1, 2)
    ax3.imshow(ring.T, origin="lower", aspect="auto", cmap="gray",
               extent=[0, 360, g["z0"], g["z0"] + occ.shape[2] * h])
    for k in range(7):
        ax3.axvline(60 * k, color="r", lw=0.5)
    ax3.set_title(f"ring r = {rs[0]:.1f} to {rs[-1]:.1f} mm unwrapped: angle (deg) vs z (mm), radial material (mm)")
    fig.tight_layout()
    fig.savefig(args.out, dpi=100)


if __name__ == "__main__":
    main()
