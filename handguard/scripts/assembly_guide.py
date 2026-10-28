"""Illustrated guide: how the two snake pieces slide on, lock, and come off.

Renders the real models (handguard, snake_rear, snake_front) on a simple stand-in
for the rifle (receiver block, barrel, muzzle device), colour-coded, with arrows
and captions, plus a cut-away of the lock screw and a cross-section showing why
the snake cannot lift off or turn. Output: renders/assembly_guide.png
"""
import os

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

GREY = np.array([0.72, 0.74, 0.77])      # handguard
DARK = np.array([0.30, 0.31, 0.33])      # rifle stand-in
GREEN = np.array([0.36, 0.66, 0.36])     # snake rear piece
ORANGE = np.array([0.93, 0.56, 0.20])    # snake front piece
RED = np.array([0.85, 0.15, 0.15])       # set screw
BG = (250, 250, 248)

VIEW = np.array([0.0, -0.86, -0.51]); UP = np.array([0.0, 0.0, 1.0])  # from the left side, a little above
LIGHT = (0.55, 0.55, 0.35)
MUZZLE_X = 415.0                          # assumed end of the barrel, for the picture only


def frame(view, up):
    view = view / np.linalg.norm(view)
    up = up - view * (up @ view); up /= np.linalg.norm(up)
    return view, up, np.cross(view, up)


def rifle_standin():
    recv = trimesh.creation.box(extents=[90, 30, 52]); recv.apply_translation([-46, 0, 6])
    barrel = trimesh.creation.cylinder(radius=9.5, height=MUZZLE_X + 30, sections=48)
    barrel.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    barrel.apply_translation([(MUZZLE_X - 30) / 2, 0, 0])
    brake = trimesh.creation.cylinder(radius=11.0, height=55, sections=48)
    brake.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    brake.apply_translation([MUZZLE_X + 27.5, 0, 0])
    return trimesh.util.concatenate([recv, barrel, brake])


class Scene:
    """Orthographic, Lambert-shaded, colour z-buffer renderer with a fixed framing."""

    def __init__(self, view, up, lo, hi, res):
        self.view, self.up, self.right = frame(np.asarray(view, float), np.asarray(up, float))
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
        u = corners @ self.right; v = corners @ self.up
        self.u0, self.v0, self.res = u.min(), v.min(), res
        self.W = int((u.max() - u.min()) / res) + 1; self.H = int((v.max() - v.min()) / res) + 1

    def px(self, p):
        p = np.atleast_2d(p)
        return np.c_[(p @ self.right - self.u0) / self.res, self.H - 1 - (p @ self.up - self.v0) / self.res]

    def render(self, items, density=4.0):
        L = -self.view * LIGHT[0] + self.up * LIGHT[1] + self.right * LIGHT[2]; L /= np.linalg.norm(L)
        pts, col, dep = [], [], []
        for mesh, color in items:
            n = min(int(density * mesh.area / self.res ** 2), 14_000_000) + 20000
            P, fi = trimesh.sample.sample_surface(mesh, n)
            nrm = mesh.face_normals[fi]
            front = nrm @ -self.view > 0
            P, nrm = P[front], nrm[front]
            sh = 0.35 + 0.65 * np.clip(nrm @ L, 0, 1)
            pts.append(P); col.append(sh[:, None] * color[None, :]); dep.append(P @ self.view)
        P = np.vstack(pts); C = np.vstack(col); D = np.concatenate(dep)
        xy = self.px(P).astype(int)
        ok = (xy[:, 0] >= 0) & (xy[:, 0] < self.W) & (xy[:, 1] >= 0) & (xy[:, 1] < self.H)
        xy, C, D = xy[ok], C[ok], D[ok]
        order = np.argsort(-D)
        img = np.zeros((self.H * self.W, 3)); img[:] = np.array(BG) / 255
        img[xy[order, 1] * self.W + xy[order, 0]] = C[order]
        return Image.fromarray((np.clip(img.reshape(self.H, self.W, 3), 0, 1) * 255).astype(np.uint8))


def arrow(draw, a, b, color, width=9):
    a = np.asarray(a, float); b = np.asarray(b, float)
    draw.line([tuple(a), tuple(b)], fill=color, width=width)
    d = (b - a) / np.linalg.norm(b - a); n = np.array([-d[1], d[0]])
    head = 4.2 * width
    draw.polygon([tuple(b + d * head * 0.4), tuple(b - d * head + n * head * 0.6), tuple(b - d * head - n * head * 0.6)], fill=color)


def caption(img, step, title, text, W=None):
    W = W or img.width
    font_b = ImageFont.truetype(FONT_B, 40); font = ImageFont.truetype(FONT, 30)
    lines = text.split("\n")
    top = 130 + 42 * len(lines)
    out = Image.new("RGB", (W, img.height + top), BG)
    out.paste(img, ((W - img.width) // 2, top))
    d = ImageDraw.Draw(out)
    if step:
        d.ellipse([28, 24, 98, 94], fill=(40, 40, 40)); d.text((63, 59), str(step), fill="white", font=font_b, anchor="mm")
    d.text((120 if step else 30, 36), title, fill=(30, 30, 30), font=font_b)
    for i, line in enumerate(lines):
        d.text((120 if step else 30, 100 + 42 * i), line, fill=(70, 70, 70), font=font)
    return out


def legend(W):
    img = Image.new("RGB", (W, 150), BG); d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 30); x, y = 30, 30
    for name, c in [("handguard (stays on the rifle)", GREY), ("snake rear piece", GREEN),
                    ("snake front piece (head)", ORANGE), ("set screw", RED), ("rifle", DARK)]:
        width = 70 + d.textlength(name, font=font)
        if x + width > W - 20:
            x, y = 30, y + 55
        rgb = tuple(int(v * 255) for v in c)
        d.rectangle([x, y, x + 40, y + 34], fill=rgb, outline=(60, 60, 60))
        d.text((x + 52, y + 17), name, fill=(40, 40, 40), font=font, anchor="lm")
        x += width
    return img


def moved(m, dx):
    m = m.copy(); m.apply_translation([dx, 0, 0]); return m


def end_view(base, rear):
    """Looking down the barrel from the muzzle: the snake grips the handguard like a C-clip."""
    sc = Scene([-1, 0, 0], UP, np.array([0, -60, -62]), np.array([400, 60, 52]), res=0.075)
    near = base.slice_plane([300, 0, 0], [-1, 0, 0], cap=True)  # the rear part of the handguard, so the coils show
    barrel = trimesh.creation.cylinder(radius=9.5, height=300, sections=64)
    barrel.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])); barrel.apply_translation([150, 0, 0])
    img = sc.render([(near, GREY), (rear, GREEN), (barrel, DARK)], density=3.0)
    d = ImageDraw.Draw(img); font = ImageFont.truetype(FONT_B, 32)
    def label(p, text, off, align="m"):
        q = sc.px(p)[0]; t = q + np.array(off)
        d.line([tuple(t), tuple(q)], fill=(30, 30, 30), width=4)
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if off[1] > 0:
                d.text((t[0], t[1] + 4 + 38 * i), line, fill=(30, 30, 30), font=font, anchor=align + "a")
            else:
                d.text((t[0], t[1] - 4 - 38 * (len(lines) - 1 - i)), line, fill=(30, 30, 30), font=font, anchor=align + "d")
    label([0, 0, 31.5], "rail: the snake stays clear of it", (0, -60))
    label([0, 18.2, 2], "flat sides + rail:\nthe snake cannot turn", (40, -330), align="l")
    label([0, -8, -32], "the snake wraps ~230 deg around,\nso it cannot be pulled off sideways", (-60, 120))
    q = sc.px([0, 0, 0])[0]
    d.text(tuple(q), "barrel", fill=(255, 255, 255), font=font, anchor="mm")
    return img


def main():
    base = trimesh.load(os.path.join(ROOT, "handguard_base.stl"))
    rear = trimesh.load(os.path.join(ROOT, "snake_rear.3mf"), force="mesh")
    front = trimesh.load(os.path.join(ROOT, "snake_front.3mf"), force="mesh")
    rifle = rifle_standin()
    lo, hi = np.array([-95.0, -40, -40]), np.array([660.0, 40, 80])
    sc = Scene(VIEW, UP, lo, hi, res=0.5)
    ax_pt = lambda x: sc.px([x, -20, 62])[0]  # arrows run just above the parts
    panels = []
    g = tuple(int(v * 255) for v in GREEN); o = tuple(int(v * 255) for v in ORANGE)

    def step(items, n, title, text, arrows=(), marks=()):
        img = sc.render(items); d = ImageDraw.Draw(img)
        for (x0, x1), color in arrows:
            arrow(d, ax_pt(x0), ax_pt(x1), color)
        font = ImageFont.truetype(FONT_B, 32)
        for p, label, off in marks:
            q = sc.px(p)[0]; t = q + np.array(off)
            d.line([tuple(t), tuple(q)], fill=(30, 30, 30), width=4)
            d.text(tuple(t), label, fill=(30, 30, 30), font=font, anchor="md")
        panels.append(caption(img, n, title, text, W=sc.W))

    step([(rifle, DARK), (base, GREY)], 1, "Start: the handguard is on the rifle",
         "Clamp the handguard on as normal. Take off anything bolted to the keymod slots.\n"
         "The snake goes on afterwards, from the muzzle end (left in these pictures).")
    step([(rifle, DARK), (base, GREY), (moved(rear, 300), GREEN)], 2, "Slide the rear piece on over the muzzle",
         "Tail end first. It slides along the handguard like a sleeve; it does not snap on.",
         arrows=[((520, 380), g)])
    step([(rifle, DARK), (base, GREY), (rear, GREEN)], 3, "Push it back until it stops",
         "It stops against the step near the receiver, where the keymod flats begin.",
         marks=[([63, 18, 2], "stops here", (40, -150))])
    step([(rifle, DARK), (base, GREY), (rear, GREEN), (moved(front, 200), ORANGE)], 4, "Slide the front piece (the head) on",
         "The barrel and muzzle device pass through the hole in the head.\n"
         "Push it back until the head sits against the end of the handguard.",
         arrows=[((650, 500), o)])
    step([(rifle, DARK), (base, GREY), (rear, GREEN), (front, ORANGE)], 5, "Tighten the one set screw on top of the head",
         "The screw drops into the last rail slot, so the head cannot slide off.\n"
         "The head in turn holds the rear piece in place. Done.",
         marks=[([370.7, 0, 41], "set screw", (0, -110))])
    step([(rifle, DARK), (base, GREY), (moved(rear, 150), GREEN), (moved(front, 200), ORANGE)], 6,
         "To take it off: loosen the screw, slide both pieces forward",
         "Front piece first, then the rear piece, off over the muzzle.",
         arrows=[((480, 620), o), ((250, 380), g)])

    # close-up: the head cut in half down the middle, showing the screw in the rail slot
    lo2, hi2 = np.array([328.0, -40, -45]), np.array([452.0, 40, 80])
    sc2 = Scene([0, 1, 0], UP, lo2, hi2, res=0.1)
    half = lambda m: m.slice_plane([0, 0, 0], [0, 1, 0], cap=True)
    screw = trimesh.creation.cylinder(radius=2.4, height=11.0, sections=40); screw.apply_translation([370.7, 0, 34.0])
    near = lambda m: m.slice_plane([330, 0, 0], [1, 0, 0])
    cut = sc2.render([(half(near(base)), GREY), (half(near(front)), ORANGE), (half(screw), RED)])
    d = ImageDraw.Draw(cut); font = ImageFont.truetype(FONT_B, 34)
    for p, label, off, align in [([370.7, 0, 41.5], "set screw", (60, -120), "l"),
                                 ([387.7, 0, -17.5], "the head's inner wall stops\nagainst the end of the handguard", (-330, 170), "l"),
                                 ([350.7, 0, 31.2], "the other rail slots stay free", (-120, -120), "l")]:
        q = sc2.px(p)[0]; t = q + np.array(off)
        d.line([tuple(t), tuple(q)], fill=(30, 30, 30), width=4)
        lines = label.split("\n")
        for i, line in enumerate(lines):
            if off[1] > 0:
                d.text((t[0], t[1] + 4 + 40 * i), line, fill=(30, 30, 30), font=font, anchor=align + "a")
            else:
                d.text((t[0], t[1] - 4 - 40 * (len(lines) - 1 - i)), line, fill=(30, 30, 30), font=font, anchor=align + "d")
    panels.append(caption(cut, None, "Close-up, head cut in half (from the left side)",
                          "The screw (red) goes through the top of the head into the last rail slot.\n"
                          "The head's inner wall rests against the end of the handguard.", W=sc.W))

    panels.append(caption(end_view(base, rear), None, "Why it cannot fall off or spin",
                          "Looking down the barrel from the muzzle. The snake hugs the handguard with a 0.35 mm gap,\n"
                          "so it can only slide forward and back. The flat sides and the rail stop it turning.", W=sc.W))

    W = max(p.width for p in panels)
    title = Image.new("RGB", (W, 110), BG); ImageDraw.Draw(title).text(
        (30, 55), "Snake handguard: fitting and removing the snake", fill=(20, 20, 20),
        font=ImageFont.truetype(FONT_B, 52), anchor="lm")
    blocks = [title, legend(W)]
    for p in panels:
        if p.width < W:
            q = Image.new("RGB", (W, p.height), BG); q.paste(p, ((W - p.width) // 2, 0)); p = q
        blocks += [p, Image.new("RGB", (W, 6), (215, 215, 212))]
    out = Image.new("RGB", (W, sum(b.height for b in blocks)), BG)
    y = 0
    for b in blocks:
        out.paste(b, (0, y)); y += b.height
    path = os.path.join(ROOT, "renders", "assembly_guide.png")
    out.save(path, optimize=True)
    print(path, out.size)


if __name__ == "__main__":
    main()
