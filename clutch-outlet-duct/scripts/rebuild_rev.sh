set -e
cp sdf_s_orig.npy sdf_s.npy; cp Fa_orig.npy Fa.npy; cp dall_orig.npy dall.npy
python3 sweepfit.py | tail -14
python3 sweepapply.py
python3 upsec.py && python3 build5.py && python3 addtab.py
python3 spikes.py W4.npy > /dev/null || true
python3 cleanup.py && python3 final_mesh.py W5.npy && python3 export.py && cp final_export.stl final_export_sweep.stl
python3 mls.py final_export_sweep.stl sweep_mls.ply 15.0 -40 2
python3 mls.py sweep_mls.ply sweep_mls2.ply 30.0 circled_pts.npy 2 2.0
echo REBUILD_OK
