"""Strength check of the printed handguard: beam analysis from real cross-sections.

The handguard is a cantilever: clamped on the barrel nut at the rear, free at the muzzle
end. The mesh is sliced every 0.5 mm along the bore axis; each slice gives the section's
area and second moments of area about its centroid (Green's theorem on the polygons).

Load cases (all forces at the muzzle end, X = 380 mm):
  * side or vertical push of 200 N (about 20 kg), e.g. leaning the rifle on a barricade
  * recoil: the parts' own mass at 100 g along the bore axis (handguard + snake)

Reports the weakest section, the peak bending stress, the tip deflection, and the safety
factor against a conservative strength of printed PA-CF across layers (40 MPa).
"""
import argparse
import json

import numpy as np
import trimesh

E_MPA = 5000.0          # printed PA-CF, along the layers (conservative)
STRENGTH_MPA = 40.0     # printed PA-CF, weakest direction (across layers)
X_CLAMP = 31.3          # middle of the clamp, where the cantilever is held
X_LOAD = 380.0
F_N = 200.0


def section_props(polys):
    """Area, centroid and second moments (about the centroid) of a set of shapely polygons."""
    A = Sy = Sz = Iyy = Izz = 0.0
    for p in polys:
        for ring, sgn in [(p.exterior, 1.0)] + [(r, -1.0) for r in p.interiors]:
            y, z = np.asarray(ring.xy)
            a = y[:-1] * z[1:] - y[1:] * z[:-1]
            orient = np.sign(a.sum()) or 1.0
            a = a * orient * sgn
            A += a.sum() / 2
            Sy += ((y[:-1] + y[1:]) * a).sum() / 6
            Sz += ((z[:-1] + z[1:]) * a).sum() / 6
            Iyy += ((z[:-1] ** 2 + z[:-1] * z[1:] + z[1:] ** 2) * a).sum() / 12   # about the Y axis (vertical bending)
            Izz += ((y[:-1] ** 2 + y[:-1] * y[1:] + y[1:] ** 2) * a).sum() / 12   # about the Z axis (side bending)
    if A <= 0:
        return 0, 0, 0, 0, 0
    cy, cz = Sy / A, Sz / A
    return A, cy, cz, Iyy - A * cz ** 2, Izz - A * cy ** 2


def sections(mesh, x0, x1, step=0.5):
    out = []
    for x in np.arange(x0, x1, step):
        sec = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
        if sec is None:
            out.append((x, 0, 0, 0, 0, 0, 0, 0)); continue
        planar, _ = sec.to_2D(to_2D=np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -x], [0, 0, 0, 1]], float))
        polys = planar.polygons_full
        A, cy, cz, Iyy, Izz = section_props(polys)
        cmax_z = max(abs(np.asarray(p.exterior.xy)[1] - cz).max() for p in polys) if polys else 0
        cmax_y = max(abs(np.asarray(p.exterior.xy)[0] - cy).max() for p in polys) if polys else 0
        out.append((x, A, Iyy, Izz, cmax_z, cmax_y, len(polys), cz))
    return np.array(out)


def analyse(path, snake_mass_kg=0.0):
    m = trimesh.load(path, force="mesh")
    S = sections(m, X_CLAMP, X_LOAD, 0.5)
    x, A, Iyy, Izz, cz, cy = S[:, 0], S[:, 1], S[:, 2], S[:, 3], S[:, 4], S[:, 5]
    M = F_N * (X_LOAD - x)                         # N*mm
    sig_v = M * cz / np.maximum(Iyy, 1e-9)          # vertical push
    sig_s = M * cy / np.maximum(Izz, 1e-9)          # side push
    # tip deflection: integrate curvature M/EI twice
    def tip(I):
        k = M / (E_MPA * np.maximum(I, 1e-9))
        return np.trapezoid(k * (X_LOAD - x), x)
    mass = m.volume / 1000 * 1.2 / 1000 * 0.75 + snake_mass_kg   # ~75 % fill
    recoil_n = mass * 100 * 9.81
    i = np.argmin(np.minimum(Iyy, Izz))
    res = {
        "file": path, "volume_cm3": round(m.volume / 1000, 1),
        "weakest_section_X_mm": round(float(x[i]), 1),
        "min_area_mm2": round(float(A.min()), 1),
        "min_I_vertical_mm4": round(float(Iyy.min())), "min_I_side_mm4": round(float(Izz.min())),
        "peak_stress_vertical_200N_MPa": round(float(sig_v.max()), 1),
        "peak_stress_side_200N_MPa": round(float(sig_s.max()), 1),
        "tip_deflection_vertical_200N_mm": round(float(tip(Iyy)), 2),
        "tip_deflection_side_200N_mm": round(float(tip(Izz)), 2),
        "safety_factor_200N": round(STRENGTH_MPA / float(max(sig_v.max(), sig_s.max())), 2),
        "recoil_inertia_N": round(recoil_n), "recoil_axial_stress_MPa": round(recoil_n / float(A.min()), 2),
    }
    return res, S


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh")
    ap.add_argument("--snake-kg", type=float, default=0.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res, S = analyse(a.mesh, a.snake_kg)
    print(json.dumps(res, indent=1))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
        np.save(a.out.replace(".json", "_sections.npy"), S)
