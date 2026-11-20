#!/usr/bin/env bash
# Corrected outlet end (revised v3). Run inside the work directory left by run_all.sh and rebuild_rev.sh
# (needs P.npy, PN.npy, outerP.npy, sdf_s_orig.npy, sdf_s.npy, grid.npy, centerline.npy, sweep_*.npz, hook_plane.npy).
# The steps were run one at a time, in this order.
set -euo pipefail
S="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
py(){ echo "== $*"; python3 "$S/$1" "${@:2}"; }
py cuff4.py        # outlet cuff axis, center and diameters from its intact walls -> cuff4.npz (copied to collar_frame.npz with the hook-plane frame)
py symfit.py       # mirror plane of the elbow, fitted on intact overlaps -> mirror_plane.npz
py end1.py         # outer solid of the outlet end: sweep tube + scan elbow + mirror completion + ideal cuff, pocket filled
py end2.py         # clean the elbow surface: refill unscanned and burned areas, robust smoothing, fairing
py end2b.py        # rebuild the solid from the cleaned surface
py end3.py end_fo2.npy   # hollow (2.5 mm wall, 3.5 mm cuff), open the bore, add the rim tab, mesh
py splice.py 80    # cut revised v2 across the tube and join the new end (everything beyond the cut is unchanged)
py v3_check.py     # verify and export final_export_v3.stl
