"""Put the raw knob scan into the model frame and strip the background.

The transform (scan_to_model.json) was found on this scan:
  1. crop the knob and remove the turntable planes (RANSAC on faces outside the knob)
  2. fit the skirt as two coaxial cones (inner and outer wall, common 4.07 deg draft);
     the cone axis is the knob axis and the back rim comes out flat to +-0.1 mm
  3. turn about the axis so the grip bar's side faces run along x (pointer at +x)
Heights are the cone fit's: z=0 is near the middle of the skirt, the bar front is z=-29.5.

Usage: python align_scan.py "Mesh_Knob Scan.stl" work/scan_aligned.ply
"""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh


def main():
    src, dst = sys.argv[1], sys.argv[2]
    cfg = json.loads((Path(__file__).with_name("scan_to_model.json")).read_text())
    scan = trimesh.load(src, process=False)
    scan.merge_vertices()
    scan.apply_transform(np.array(cfg["matrix"]))
    P, N = scan.triangles_center, scan.face_normals
    keep = (np.hypot(P[:, 0], P[:, 1]) < 34) & (P[:, 2] > -34) & (P[:, 2] < 45)
    for *n, d in cfg["background_planes"]:
        n = np.array(n)
        keep &= ~((np.abs(P @ n - d) < 0.5) & (np.abs(N @ n) > 0.7))
    out = scan.submesh([np.nonzero(keep)[0]], append=True)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    out.export(dst)
    print(f"{len(out.faces)} faces -> {dst}")


if __name__ == "__main__":
    main()
