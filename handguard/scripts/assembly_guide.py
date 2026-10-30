"""Illustrated assembly guide: parts and hardware, the heat-set insert, mounting the
handguard on the rifle, sliding on and locking the two snake pieces, and removal.

Renders the real models (handguard, snake_rear, snake_front) on a simple stand-in
for the rifle (receiver block, barrel nut, barrel, muzzle device), colour-coded, with
arrows and captions, plus a cut-away of the lock screw and an end view showing why
the snake cannot lift off or turn. Output: renders/assembly_guide.png
"""
import json
import os

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

import build_handguard as HG

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

LOCK = json.load(open(os.path.join(ROOT, "data", "snake_lock.json")))
HG_RAIL = 31.1
LX, LZ = LOCK["lock_x"], LOCK["coil_top"]
GREY = np.array([0.72, 0.74, 0.77])      # handguard
DARK = np.array([0.30, 0.31, 0.33])      # rifle stand-in
GREEN = np.array([0.36, 0.66, 0.36])     # snake rear piece
ORANGE = np.array([0.93, 0.56, 0.20])    # snake front piece
RED = np.array([0.85, 0.15, 0.15])       # set screw
BRASS = np.array([0.86, 0.68, 0.25])     # heat-set insert
STEEL = np.array([0.20, 0.35, 0.75])     # clamp screws
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
    nut = cyl_x(17.0, 0.5, 36.0)   # barrel nut
    return trimesh.util.concatenate([recv, barrel, brake, nut])


def cyl_x(r, x0, x1, y=0.0, z=0.0):
    c = trimesh.creation.cylinder(radius=r, height=x1 - x0, sections=48)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    c.apply_translation([(x0 + x1) / 2, y, z]); return c


def cyl_y(r, y0, y1, x, z):
    c = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=40)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2, z]); return c


def cyl_z(r, z0, z1, x, y):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=40)
    c.apply_translation([x, y, (z0 + z1) / 2]); return c


def clamp_screws():
    """Clamp hardware in place: two M4 x 25 bolts with captive nuts, and Jack's centre screw."""
    parts = []
    for x in HG.SCREW_X:
        y_head = -HG.BOSS_HALF + 4.0
        parts.append(cyl_y(1.9, y_head, y_head + 25.0, x, HG.SCREW_Z))             # shank
        parts.append(cyl_y(3.5, y_head - 4.0, y_head, x, HG.SCREW_Z))               # head, flush in its counterbore
        nut = trimesh.creation.cylinder(radius=7.0 / np.sqrt(3), height=3.2, sections=6)
        nut.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        nut.apply_translation([x, HG.BOSS_HALF - HG.NUT_T + 1.6, HG.SCREW_Z])
        parts.append(nut)
    parts.append(cyl_z(1.9, HG.KEEL_BOT + 3.5, -12.0, HG.CENTER_SCREW_X, 0.0))
    parts.append(cyl_z(3.5, HG.KEEL_BOT - 0.4, HG.KEEL_BOT + 4.0, HG.CENTER_SCREW_X, 0.0))
    return trimesh.util.concatenate(parts)


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
                    ("snake front piece (head)", ORANGE), ("set screw", RED), ("heat-set insert", BRASS),
                    ("clamp bolts and screw", STEEL), ("rifle", DARK)]:
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


def autocrop(img, pad=30):
    a = np.asarray(img).astype(int)
    mask = np.abs(a - np.array(BG)).sum(2) > 12
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return img
    return img.crop((max(0, xs.min() - pad), max(0, ys.min() - pad), min(img.width, xs.max() + pad), min(img.height, ys.max() + pad)))


def moved_z(m, dz):
    m = m.copy(); m.apply_translation([0, 0, dz]); return m


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
    label([0, -9.0, 30.0], "rail", (-260, -40), align="r")
    label([0, 18.2, 2], "flat sides + rail:\nthe snake cannot turn", (40, -330), align="l")
    label([0, -8, -32], "the spiral goes all the way around,\nso it cannot come off sideways", (-60, 120))
    q = sc.px([0, 0, 0])[0]
    d.text(tuple(q), "barrel", fill=(255, 255, 255), font=font, anchor="mm")
    return img


def main():
    base = trimesh.load(os.path.join(ROOT, "handguard_base.stl"))
    rear = trimesh.load(os.path.join(ROOT, "snake_rear.3mf"), force="mesh")
    front = trimesh.load(os.path.join(ROOT, "snake_front.3mf"), force="mesh")
    rifle = rifle_standin()
    lo, hi = np.array([-95.0, -40, -40]), np.array([660.0, 40, 95])
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

    screws = clamp_screws()
    brass = tuple(int(v * 255) for v in BRASS); grey = tuple(int(v * 255) for v in GREY)
    steel = tuple(int(v * 255) for v in STEEL)

    # ---- parts and hardware
    sc0 = Scene(VIEW, UP, np.array([-10.0, -60, -130]), np.array([520.0, 60, 70]), res=0.5)
    rows = [(base, GREY, 0.0, 0.0, "handguard_base.stl"),
            (rear, GREEN, 0.0, -100.0, "snake_rear.3mf"),
            (front, ORANGE, 50.0, -100.0, "snake_front.3mf")]
    items = [(moved_z(moved(m, dx), dz), c) for m, c, dx, dz, _ in rows]
    img = sc0.render(items)
    d = ImageDraw.Draw(img); fb = ImageFont.truetype(FONT_B, 30)
    for m, c, dx, dz, t in rows:
        q = sc0.px([(m.bounds[0][0] + m.bounds[1][0]) / 2 + dx, 0, m.bounds[1][2] + dz + 6])[0]
        d.text(tuple(q), t, fill=(30, 30, 30), font=fb, anchor="md")
    img = autocrop(img)
    panels.append(caption(img, None, "What you need",
                          "Printed: the handguard and the two snake pieces.\n"
                          "Hardware: 2 x M4 x 25 socket head bolts + 2 x M4 hex nuts (clamp), Jack's original centre\n"
                          "screw, one M5 heat-set insert (6.4 mm hole, 6 mm deep), one M5 x 12 set screw (cup or flat point),\n"
                          "blue (medium) thread locker.\n"
                          "Tools: soldering iron (for the insert), hex keys for the bolts, nut and set screw.", W=sc.W))

    # ---- 1. heat-set insert
    sci = Scene([0.25, -0.62, -0.74], UP, np.array([LX - 30, -32, LZ - 30]), np.array([LX + 30, 32, LZ + 24]), res=0.09)
    f_near = front.slice_plane([LX - 40, 0, 0], [1, 0, 0]).slice_plane([LX + 40, 0, 0], [-1, 0, 0])
    ins = cyl_z(3.2, LZ + 10, LZ + 16, LX, 0.0)
    img = sci.render([(f_near, ORANGE), (ins, BRASS)], density=3.0)
    d = ImageDraw.Draw(img)
    arrow(d, sci.px([LX, 0, LZ + 9])[0], sci.px([LX, 0, LZ + 1.5])[0], brass, width=10)
    q = sci.px([LX, 3.2, LZ + 13])[0]
    d.text((q[0] + 40, q[1]), "M5 heat-set insert", fill=(30, 30, 30), font=fb, anchor="lm")
    q = sci.px([LX, 0, LZ])[0]
    d.line([(q[0] - 25, q[1] + 10), (q[0] - 120, q[1] + 120)], fill=(30, 30, 30), width=4)
    d.text((q[0] - 130, q[1] + 130), "hole on top of the last coil", fill=(30, 30, 30), font=fb, anchor="ra")
    img = autocrop(img)
    panels.append(caption(img, 1, "Before you start: put the insert into the head piece",
                          "Set the insert on the hole on top of the last coil of the front (orange) piece. Press it\n"
                          "straight down with a soldering iron (about 230 C for PA-CF/PC) until it is flush. Let it cool.\n"
                          "Do this once; the set screw threads into it every time you fit the snake.", W=sc.W))

    # ---- 2. handguard onto the barrel nut
    step([(rifle, DARK), (moved(base, 110), GREY)], 2, "Slide the handguard over the barrel and onto the barrel nut",
         "Muzzle device off if it is larger than the bore. Slide it back until the two small tabs at its rear end\n"
         "sit against the front of the receiver, with the top rail lined up with the receiver's rail.",
         arrows=[((300, 170), grey)])

    # ---- 3. clamp screws
    scc = Scene([0.15, 0.55, 0.82], UP, np.array([-5.0, -32, -36]), np.array([75.0, 32, 30]), res=0.07)
    b_near = base.slice_plane([80, 0, 0], [-1, 0, 0])
    img = scc.render([(b_near, GREY), (screws, STEEL), (rifle.slice_plane([80, 0, 0], [-1, 0, 0]), DARK)], density=3.0)
    d = ImageDraw.Draw(img)
    for x in HG.SCREW_X:
        q = scc.px([x, -HG.BOSS_HALF - 0.6, HG.SCREW_Z])[0]
        arrow(d, q + np.array([0, 150]), q + np.array([0, 40]), steel, width=8)
    q = scc.px([HG.SCREW_X[1], -HG.BOSS_HALF, HG.SCREW_Z])[0]
    d.text((q[0] + 60, q[1] + 150), "2 x M4 bolts (nuts on the far side)", fill=(30, 30, 30), font=fb, anchor="lm")
    q = scc.px([HG.CENTER_SCREW_X, 0, HG.KEEL_BOT])[0]
    arrow(d, q + np.array([-170, 60]), q + np.array([-45, 10]), steel, width=8)
    d.text((q[0] - 180, q[1] + 70), "centre screw", fill=(30, 30, 30), font=fb, anchor="rm")
    img = autocrop(img)
    panels.append(caption(img, 3, "Tighten the clamp (seen from below, right side)",
                          "Drop the two M4 nuts into the hex pockets on the left side of the clamp. Put the M4 x 25 bolts\n"
                          "in from the right with a drop of blue thread locker and tighten them a little at a time,\n"
                          "alternating, to about 2 N m (firm, not cranked). Then put Jack's centre screw back in from below.\n"
                          "Check the rail is lined up with the receiver. Re-check the bolts after the first range trip.", W=sc.W))

    # ---- 4 to 7: the snake
    step([(rifle, DARK), (base, GREY), (moved(rear, 300), GREEN)], 4, "Slide the rear snake piece on over the muzzle",
         "Tail end first. It slides along the handguard like a sleeve; it does not snap on.\n"
         "Take off anything bolted to the keymod slots first.",
         arrows=[((520, 380), g)])
    step([(rifle, DARK), (base, GREY), (rear, GREEN)], 5, "Push it back until it stops",
         "It stops against the step near the receiver, where the keymod flats begin.",
         marks=[([63, 18, 2], "stops here", (40, -150))])
    step([(rifle, DARK), (base, GREY), (rear, GREEN), (moved(front, 200), ORANGE)], 6, "Slide the front piece (the head) on",
         "The barrel and muzzle device pass through the hole in the head.\n"
         "Push it back until the head sits against the end of the handguard.",
         arrows=[((650, 500), o)])
    step([(rifle, DARK), (base, GREY), (rear, GREEN), (front, ORANGE)], 7, "Tighten the set screw in the last coil",
         "It goes through the insert into the rail slot under the last coil, so the head\n"
         "cannot slide off. The head in turn holds the rear piece in place. Snug is enough. Done.",
         marks=[([LX, 0, LZ], "set screw", (60, -60))])
    step([(rifle, DARK), (base, GREY), (moved(rear, 150), GREEN), (moved(front, 200), ORANGE)], 8,
         "To take the snake off: loosen the screw, slide it forward",
         "Front piece first, then the rear piece, off over the muzzle. The handguard stays on the rifle.",
         arrows=[((480, 620), o), ((250, 380), g)])

    # close-up: the head cut in half down the middle, showing the screw in the rail slot
    lo2, hi2 = np.array([328.0, -40, -45]), np.array([452.0, 40, 80])
    sc2 = Scene([0, 1, 0], UP, lo2, hi2, res=0.1)
    half = lambda m: m.slice_plane([0, 0, 0], [0, 1, 0], cap=True)
    screw = trimesh.creation.cylinder(radius=2.4, height=11.0, sections=40); screw.apply_translation([LX, 0, HG_RAIL + 5.5])
    near = lambda m: m.slice_plane([330, 0, 0], [1, 0, 0])
    cut = sc2.render([(half(near(base)), GREY), (half(near(front)), ORANGE), (half(screw), RED)])
    d = ImageDraw.Draw(cut); font = ImageFont.truetype(FONT_B, 34)
    for p, label, off, align in [([LX, 0, LZ], "set screw", (60, -120), "l"),
                                 ([387.7, 0, -17.5], "the head's inner wall stops\nagainst the end of the handguard", (-330, 170), "l")]:
        q = sc2.px(p)[0]; t = q + np.array(off)
        d.line([tuple(t), tuple(q)], fill=(30, 30, 30), width=4)
        lines = label.split("\n")
        for i, line in enumerate(lines):
            if off[1] > 0:
                d.text((t[0], t[1] + 4 + 40 * i), line, fill=(30, 30, 30), font=font, anchor=align + "a")
            else:
                d.text((t[0], t[1] - 4 - 40 * (len(lines) - 1 - i)), line, fill=(30, 30, 30), font=font, anchor=align + "d")
    panels.append(caption(cut, None, "Close-up, head cut in half (from the left side)",
                          "The screw (red) goes down through the last coil into the rail slot under it.\n"
                          "The head's inner wall rests against the end of the handguard.", W=sc.W))

    panels.append(caption(end_view(base, rear), None, "Why it cannot fall off or spin",
                          "Looking down the barrel from the muzzle (rear piece only). The snake hugs the handguard with a\n"
                          "0.35 mm gap, so it can only slide forward and back. The flat sides and the rail stop it turning.", W=sc.W))

    W = max(p.width for p in panels)
    title = Image.new("RGB", (W, 110), BG); ImageDraw.Draw(title).text(
        (30, 55), "Snake handguard: how it all goes together", fill=(20, 20, 20),
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
