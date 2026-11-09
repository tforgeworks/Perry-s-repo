#!/usr/bin/env bash
# Rebuild polaris_5439157_outlet_duct_repaired.stl from the scan.
# Usage: bash run_all.sh <work-dir>   (needs about 16 GB RAM, 30 GB disk, ~40 min on 4 cores)
# pip install numpy scipy trimesh scikit-image matplotlib networkx fast_simplification pymeshfix rtree
set -euo pipefail
S="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${1:-work}"; mkdir -p "$WORK"; cd "$WORK"
py(){ echo "== $*"; python3 "$S/$1" "${@:2}"; }
cp "$S/params_in.json" .
bash "$S/get_scan.sh"
py load.py Mesh_Tressa.stl        # vertices/faces, dedupe
py norms.py                       # vertex normals
py dec.py                         # 600k-face copy for alignment
py align_full.py                  # principal-axis working frame (pca_T.npy)
py splat.py                       # fine voxel grid (0.35 mm)
# pass 1: solid fill of the outer skin (ray voting from 12 directions), outer-surface distance field
py vote2.py; py outerpts.py; py sdf.py; py smooth.py; py showsdf.py sdf_s.npy sdfs 2; py gaps.py
py make_cap_pts.py                # close the rectangular mouth for the next fill pass
# outlet geometry: centerline, minimum-area sections, end frame
py skel.py; py xsec.py; py minsec.py; py endrings.py
# pass 2 with the mouth closed
py vote2.py; py outerpts.py; py sdf.py; py smooth.py; py showsdf.py sdf_s.npy sdfs 2; py gaps.py
py fillpts.py; py orient_fill.py  # smooth fill for areas the scanner did not reach
py gappts.py; py vote2.py; py outerpts.py
# wall field from every scanned face, rebuilt outlet, final mesh
py fa.py; py upsec.py; py wfill.py; py crotch_pts.py; py wfill2.py; py dall.py
py build.py; py final_mesh.py; py export.py
py verify.py; py devfig.py; py hero.py
echo "result: $(pwd)/final_export.stl"
