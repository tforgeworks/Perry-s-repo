"""Bipod rail version of the snake: the snake is cut away under the front of the handguard.

The rifle in the scan carries a Picatinny accessory rail on the bottom keymod holes at the front
of the handguard (X 257 to 376 mm, 21 mm wide, hanging 9.7 mm below the bottom flat), which
carries the bipod. In this version everything of the snake below the handguard's bottom face is
deleted from X 255.5 to 378 mm, below Z = -15 mm: one straight, level cut, so the rail and the bipod go on and off
with the snake in place. Only the head piece changes; it stays one part (the bodies still join
above the cut along the sides). The rear piece is the standard one.

Writes snake_front_bipod_rail.3mf, data/bipod_rail.json and work/assembled_bipod_rail.stl.
"""
import json
import os

import trimesh
from manifold3d import Manifold

import build_handguard as HG
import build_snake as BS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

RAIL_X = (257.2, 376.1)        # measured on the scan (accessory rail below the bottom flat)
RAIL_HALF_W = 10.9             # measured; Picatinny is 21.2 mm wide
RAIL_BOTTOM_Z = -28.2          # measured
CUT_X = (255.5, 378.0)         # the cut: the rail plus clearance at each end
CUT_Z = -15.0                  # level cut 3.5 mm above the handguard's bottom face (-18.55): nothing of the
                               # snake below it, and the cut meets the snake's curved inside at about 40 deg
                               # (a cut level with the bottom face leaves feather-thin edges along it)


def main():
    base = HG.build(json.load(open(os.path.join(ROOT, "data", "hole_templates.json"))))
    rail = Manifold.cube((RAIL_X[1] - RAIL_X[0], 2 * RAIL_HALF_W, -HG.FLAT_BOT - RAIL_BOTTOM_Z)) \
        .translate((RAIL_X[0], -RAIL_HALF_W, RAIL_BOTTOM_Z))
    cut = Manifold.cube((CUT_X[1] - CUT_X[0], 200.0, 100.0)).translate((CUT_X[0], -100.0, CUT_Z - 100.0))
    front = BS.to_manifold(trimesh.load(os.path.join(ROOT, "snake_front.3mf"), force="mesh"))
    out = front - cut
    parts = sorted(out.decompose(), key=lambda p: -p.volume())
    tm = HG.to_trimesh(parts[0])
    print(f"head piece: removed {front.volume() - out.volume():.0f} mm3, parts {len(parts)} "
          f"{[round(p.volume(), 2) for p in parts[1:5]]}, watertight {tm.is_watertight}, "
          f"rail overlap {(parts[0] ^ rail).volume():.3f} mm3, handguard overlap {(parts[0] ^ base).volume():.3f} mm3")
    tm.export(os.path.join(ROOT, "snake_front_bipod_rail.3mf"))
    json.dump({"rail_x": RAIL_X, "rail_half_width": RAIL_HALF_W, "rail_bottom_z": RAIL_BOTTOM_Z,
               "cut_x": CUT_X, "cut_z": round(CUT_Z, 2)},
              open(os.path.join(ROOT, "data", "bipod_rail.json"), "w"), indent=1)
    rear = trimesh.load(os.path.join(ROOT, "snake_rear.3mf"), force="mesh")
    trimesh.util.concatenate([HG.to_trimesh(base), HG.to_trimesh(rail), rear, tm]) \
        .export(os.path.join(ROOT, "work", "assembled_bipod_rail.stl"))


if __name__ == "__main__":
    main()
