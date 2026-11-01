"""Bipod-rail version of the snake: a rail-shaped channel along the underside of both pieces.

The rifle in the scan carries a Picatinny accessory rail on the bottom keymod holes at the front
of the handguard (X 257 to 376 mm, 21 mm wide, hanging 9.7 mm below the bottom flat). In this
version the rail is fitted first and both snake pieces slide on over it: the channel runs the
full length of their undersides (everything behind the rail's front end passes over the rail
on the way in). The bodies still bridge under the rail at the crossings, so each piece stays in
one part; a bipod clamps onto the rail where the snake leaves it open.

Writes snake_rear_bipod_rail.3mf, snake_front_bipod_rail.3mf and data/bipod_rail.json.
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
SIDE_CLEAR, BOTTOM_CLEAR = 0.7, 1.1
CH_HALF_W = RAIL_HALF_W + SIDE_CLEAR       # channel: |Y| < 11.6
CH_BOTTOM = RAIL_BOTTOM_Z - BOTTOM_CLEAR   # channel floor Z -29.3
CH_FRONT = RAIL_X[1] + 1.4                 # channel ends 1.4 mm in front of the rail


def channel():
    lo = np.array([-20.0, -CH_HALF_W, CH_BOTTOM]); hi = np.array([CH_FRONT, CH_HALF_W, -HG.FLAT_BOT + 0.2])
    return Manifold.cube(tuple(hi - lo)).translate(tuple(lo))


def open_stretches(pieces, half_w=20.0, z=(-45.0, -19.0), step=1.0):
    """X ranges along the rail with no snake under or beside it (|Y| < half_w, Z in z):
    where a bipod clamp can go."""
    region = Manifold.cube((RAIL_X[1] - RAIL_X[0], 2 * half_w, z[1] - z[0])).translate((RAIL_X[0], -half_w, z[0]))
    near = [p ^ region for p in pieces]
    out, start = [], None
    for x in np.arange(RAIL_X[0], RAIL_X[1], step):
        sl = Manifold.cube((step, 2 * half_w, z[1] - z[0])).translate((x, -half_w, z[0]))
        o = any((p ^ sl).volume() > 0.05 for p in near)
        if not o and start is None:
            start = x
        if o and start is not None:
            out.append((round(float(start), 1), round(float(x), 1))); start = None
    if start is not None:
        out.append((round(float(start), 1), round(float(RAIL_X[1]), 1)))
    return out


def main():
    ch = channel()
    base = HG.build(json.load(open(os.path.join(ROOT, "data", "hole_templates.json"))))
    rail = Manifold.cube((RAIL_X[1] - RAIL_X[0], 2 * RAIL_HALF_W, -HG.FLAT_BOT - RAIL_BOTTOM_Z)) \
        .translate((RAIL_X[0], -RAIL_HALF_W, RAIL_BOTTOM_Z))
    pieces = {}
    for name in ("rear", "front"):
        m = BS.to_manifold(trimesh.load(os.path.join(ROOT, f"snake_{name}.3mf"), force="mesh"))
        cut = m - ch
        parts = sorted(cut.decompose(), key=lambda p: -p.volume())
        tm = HG.to_trimesh(parts[0])
        print(f"{name}: removed {m.volume() - cut.volume():.0f} mm3, parts {len(parts)} "
              f"{[round(p.volume(), 1) for p in parts[1:4]]}, watertight {tm.is_watertight}, "
              f"rail overlap {(parts[0] ^ rail).volume():.3f} mm3, handguard overlap {(parts[0] ^ base).volume():.3f} mm3")
        tm.export(os.path.join(ROOT, f"snake_{name}_bipod_rail.3mf"))
        pieces[name] = parts[0]
    stretches = open_stretches(list(pieces.values()))
    print("rail open for a bipod clamp (X, |Y| < 20 mm):", stretches)
    json.dump({"rail_x": RAIL_X, "rail_half_width": RAIL_HALF_W, "rail_bottom_z": RAIL_BOTTOM_Z,
               "channel_half_width": CH_HALF_W, "channel_floor_z": CH_BOTTOM, "channel_front_x": CH_FRONT,
               "open_for_bipod_x": stretches},
              open(os.path.join(ROOT, "data", "bipod_rail.json"), "w"), indent=1)
    asm = trimesh.util.concatenate([HG.to_trimesh(base), HG.to_trimesh(rail)] + [HG.to_trimesh(p) for p in pieces.values()])
    asm.export(os.path.join(ROOT, "work", "assembled_bipod_rail.stl"))


if __name__ == "__main__":
    main()
