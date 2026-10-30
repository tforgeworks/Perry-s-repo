"""Preview renders of the assembled snake handguard for the README (renders/snake_*.png).

Uses work/assembled_preview.stl (written by build_double_helix.py) and the two snake pieces.
Views are named after the rifle's side that faces the camera: +Y is the rifle's left.
"""
import os

import numpy as np
import trimesh
from PIL import Image

from render_util import render_mesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "renders")
N = 16_000_000


def main():
    asm = trimesh.load(os.path.join(ROOT, "work", "assembled_preview.stl"))
    rear = trimesh.load(os.path.join(ROOT, "snake_rear.3mf"), force="mesh")
    front = trimesh.load(os.path.join(ROOT, "snake_front.3mf"), force="mesh")
    base = trimesh.load(os.path.join(ROOT, "handguard_base.stl"))
    p = lambda name: os.path.join(OUT, name)
    render_mesh(asm, [-0.6, -0.55, -0.35], [0, 0, 1], res=0.25, out=p("snake_perspective.png"), n=N)
    render_mesh(asm, [0, -1, 0], [0, 0, 1], res=0.25, out=p("snake_left.png"), n=N)
    render_mesh(asm, [0, 1, 0], [0, 0, 1], res=0.25, out=p("snake_right.png"), n=N)
    for name, view, up in (("snake_top.png", [0, 0, -1], [1, 0, 0]), ("snake_bottom.png", [0, 0, 1], [1, 0, 0])):
        im = render_mesh(asm, view, up, res=0.25, n=N)
        im.rotate(90, expand=True).save(p(name))
    # head close-ups (the head piece only, so the handguard does not hide the mouth)
    head = front.slice_plane([355.0, 0, 0], [1, 0, 0], cap=True)
    render_mesh(head, [-0.75, -0.55, -0.25], [0, 0, 1], res=0.07, out=p("snake_head.png"), n=N)
    render_mesh(head, [0, 1, 0], [0, 0, 1], res=0.07, out=p("snake_head_side.png"), n=N)
    render_mesh(head, [-1, 0, 0], [0, 0, 1], res=0.07, out=p("snake_head_front.png"), n=N)
    # the tails at the rear end
    tail = trimesh.util.concatenate([base.slice_plane([110.0, 0, 0], [-1, 0, 0]), rear.slice_plane([110.0, 0, 0], [-1, 0, 0])])
    render_mesh(tail, [0.55, -0.6, -0.55], [0, 0, 1], res=0.08, out=p("snake_tail.png"), n=N)
    # exploded: handguard, rear piece, head piece pulled forward
    ex = trimesh.util.concatenate([base, rear.copy().apply_translation([60, 0, 0]),
                                   front.copy().apply_translation([140, 0, 0])])
    render_mesh(ex, [-0.6, -0.55, -0.35], [0, 0, 1], res=0.3, out=p("snake_exploded.png"), n=N)
    # Jack's concept over the model, same side and orientation (muzzle to the right)
    concept = Image.open(os.path.join(ROOT, "data", "meshy_input_concept.jpg")).convert("RGB")
    side = Image.open(p("snake_right.png")).convert("RGB")
    W = 1600
    concept = concept.resize((W, int(concept.height * W / concept.width)))
    side = side.resize((W, int(side.height * W / side.width)))
    both = Image.new("RGB", (W, concept.height + side.height + 20), (30, 30, 30))
    both.paste(concept, (0, 0)); both.paste(side, (0, concept.height + 20))
    both.save(p("concept_vs_model.png"))
    print("renders written to", OUT)


if __name__ == "__main__":
    main()
