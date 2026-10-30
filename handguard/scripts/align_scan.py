"""Align the raw handguard scan to the model frame used by build_handguard.py.

Frame: X along the bore axis (rear at X=0), Z toward the Picatinny rail, Y lateral.
Steps (values were fitted on Handguard_JackBeard.stl):
  1. PCA of the area-weighted triangle centroids gives the long axis (stored below).
  2. The bore axis is refined from circle fits of the plain rear tube (centre drift
     of -0.0140 mm/mm in the PCA frame); the rail top drifts by the same amount.
  3. Roll: the mean normal of the rail top faces is 4.30 deg off vertical; rotate it
     back so the rail is level.
  4. Shift X so the rearmost point is at X=0.

Writes an (n,3,3) float32 triangle array (.npy) for verify.py and measure_templates.py.
"""
import argparse
import struct

import numpy as np

# PCA of the scan (area-weighted centroid and principal axes), stored so the frame is exact
PCA_MEAN = np.array([19.59434, 52.93496, -430.07098])
PCA_AXES = np.array([[-0.5772856, 0.81634986, 0.017726002],
                     [0.2736094, 0.17293936, 0.94616586],
                     [0.7693369, 0.55105793, -0.32319638]])
AXIS_POINT_PCA = np.array([-183.0, -10.052, 2.557])  # a point on the bore axis, PCA frame
AXIS_SLOPE_Y = -0.0140
ROLL_DEG = -4.30


def load_stl(path):
    with open(path, "rb") as f:
        n = struct.unpack("<I", f.read(84)[80:84])[0]
    dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    return np.fromfile(path, dtype=dt, offset=84, count=n)["v"].astype(np.float64)


def align(T):
    Tl = (T - PCA_MEAN) @ PCA_AXES.T
    d = np.array([1.0, AXIS_SLOPE_Y, 0.0]); d /= np.linalg.norm(d)
    up = np.array([0, 1.0, 0]); up -= d * (up @ d); up /= np.linalg.norm(up)
    R = np.vstack([d, np.cross(up, d), up])
    Tn = (Tl - AXIS_POINT_PCA) @ R.T
    a = np.radians(ROLL_DEG)
    y = Tn[..., 1] * np.cos(a) - Tn[..., 2] * np.sin(a)
    z = Tn[..., 1] * np.sin(a) + Tn[..., 2] * np.cos(a)
    Tn[..., 1], Tn[..., 2] = y, z
    Tn[..., 0] -= Tn[..., 0].min()
    return Tn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scan")
    ap.add_argument("--out", default="tris_al.npy")
    a = ap.parse_args()
    Tn = align(load_stl(a.scan))
    np.save(a.out, Tn.astype(np.float32))
    print("aligned", len(Tn), "triangles, bounds", Tn.reshape(-1, 3).min(0).round(2), Tn.reshape(-1, 3).max(0).round(2))


if __name__ == "__main__":
    main()
