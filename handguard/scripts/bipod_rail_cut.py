"""Bipod rail version of the snake: the snake is cut away along the whole bottom of the handguard.

The rifle in the scan carries a Picatinny accessory rail on the bottom keymod holes at the front
of the handguard (X 257 to 376 mm), which carries the bipod. In this version everything of the
snake below Z = -15 mm (3.5 mm above the handguard's bottom face) is deleted along the whole
handguard, up to X 378 mm: one straight, level cut through all four loops under the handguard, so
the bottom is uniform and the rail and bipod go on and off with the snake in place. The head (in
front of the handguard) is kept.

With the bottom crossing at X 88 mm gone, the rear-most loop with the two tails would no longer
join the rest of the rear piece, so a short strip (BRIDGE) hugging the handguard just above the cut,
on each side, joins them: the rear piece stays one part.

Writes snake_rear_bipod_rail.3mf, snake_front_bipod_rail.3mf, data/bipod_rail.json and
work/assembled_bipod_rail.stl.
"""
import json
import os

import numpy as np
import trimesh
from manifold3d import Manifold

import build_handguard as HG
import build_snake as BS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

RAIL_X = (257.2, 376.1)        # measured on the scan (accessory rail below the bottom flat)
RAIL_HALF_W = 10.9             # measured; Picatinny is 21.2 mm wide
RAIL_BOTTOM_Z = -28.2          # measured
CUT_X = (-10.0, 378.0)         # the whole handguard, up to just past the rail's front end
BRIDGE = dict(x=(77.0, 97.0), z=(-15.0, -8.5), r=(19.5, 27.0))   # strip on each side joining the last loop
CUT_Z = -15.0                  # level cut 3.5 mm above the handguard's bottom face (-18.55): nothing of the
                               # snake below it, and the cut meets the snake's curved inside at about 40 deg
                               # (a cut level with the bottom face leaves feather-thin edges along it)


def slides_clear(moving, fixed, dist=40.0, step=0.25):
    """Largest overlap (mm3) while `moving` slides back into place along -X from `dist` mm forward."""
    worst = 0.0
    for dx in np.arange(step, dist + step, step):
        worst = max(worst, (moving.translate((dx, 0, 0)) ^ fixed).volume())
    return worst


def main():
    base = HG.build(json.load(open(os.path.join(ROOT, "data", "hole_templates.json"))))
    rail = Manifold.cube((RAIL_X[1] - RAIL_X[0], 2 * RAIL_HALF_W, -HG.FLAT_BOT - RAIL_BOTTOM_Z)) \
        .translate((RAIL_X[0], -RAIL_HALF_W, RAIL_BOTTOM_Z))
    cut = Manifold.cube((CUT_X[1] - CUT_X[0], 200.0, 100.0)).translate((CUT_X[0], -100.0, CUT_Z - 100.0))
    pieces = {}
    for name in ("rear", "front"):
        m = BS.to_manifold(trimesh.load(os.path.join(ROOT, f"snake_{name}.3mf"), force="mesh"))
        out = m - cut
        if name == "rear":
            (x0, x1), (z0, z1), (r0, r1) = BRIDGE["x"], BRIDGE["z"], BRIDGE["r"]
            shell = HG.cyl_x(r1, x0, x1) - HG.cyl_x(r0, x0 - 1, x1 + 1)
            band = shell ^ Manifold.cube((x1 - x0 + 2, 80.0, z1 - z0)).translate((x0 - 1, -40.0, z0))
            out = out + (band - BS.handguard_envelope())
        parts = sorted(out.decompose(), key=lambda p: -p.volume())
        print(f"{name}: removed {m.volume() - out.volume():.0f} mm3, parts {[round(p.volume()) for p in parts]}")
        big = [p for p in parts if p.volume() > 50.0]
        assert len(big) == 1, f"{name}: split into {len(big)} parts"
        pieces[name] = big[0]
    for name, p in pieces.items():
        tm = HG.to_trimesh(p)
        lo, hi = np.asarray(tm.bounds)
        print(f"  {name}: watertight {tm.is_watertight}, volume {p.volume() / 1000:.1f} cm3, X {lo[0]:.1f} to {hi[0]:.1f}, "
              f"rail overlap {(p ^ rail).volume():.3f}, handguard overlap {(p ^ base).volume():.3f} mm3")
        tm.export(os.path.join(ROOT, f"snake_{name}_bipod_rail.3mf"))
    # fitting order: tail piece, rear piece, head piece, each slid back from the muzzle end
    order = list(pieces)
    for i in range(1, len(order)):
        placed = pieces[order[0]]
        for q in order[1:i]:
            placed = placed + pieces[q]
        print(f"  sliding {order[i]} into place past {order[:i]}: worst overlap {slides_clear(pieces[order[i]], placed):.3f} mm3")
    json.dump({"rail_x": RAIL_X, "rail_half_width": RAIL_HALF_W, "rail_bottom_z": RAIL_BOTTOM_Z,
               "cut_x": CUT_X, "cut_z": CUT_Z, "pieces": list(pieces)},
              open(os.path.join(ROOT, "data", "bipod_rail.json"), "w"), indent=1)
    trimesh.util.concatenate([HG.to_trimesh(base), HG.to_trimesh(rail)] + [HG.to_trimesh(p) for p in pieces.values()]) \
        .export(os.path.join(ROOT, "work", "assembled_bipod_rail.stl"))


if __name__ == "__main__":
    main()
