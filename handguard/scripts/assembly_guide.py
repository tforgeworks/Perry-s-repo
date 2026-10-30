"""Illustrated assembly guide: parts and hardware, the heat-set inserts, mounting the
handguard on the rifle, sliding on and bolting the two snake pieces, and removal.

Renders the real models (handguard, snake_rear, snake_front) on a simple stand-in
for the rifle (receiver block, barrel nut, barrel, muzzle device), colour-coded, with
arrows and captions, plus close-ups of the joint (four alignment tabs) and of a side bolt
in its keymod hole, and an end view showing why the snake cannot lift off or turn.
Output: renders/assembly_guide.png
"""
import json
import os

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

import build_handguard as HG

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("GUIDE_ROOT", os.path.join(HERE, ".."))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

LOCK = json.load(open(os.path.join(ROOT, "data", "snake_lock.json")))
BOLTS = LOCK["bolts"]       # per piece: a left and a right M5 screw into side keymod holes
TABS = LOCK["tabs"]         # four alignment tabs on the front piece, pockets in the rear piece
TAB_W, TAB_H, TAB_L = LOCK["tab_size_mm"]
GREY = np.array([0.72, 0.74, 0.77])      # handguard
DARK = np.array([0.30, 0.31, 0.33])      # rifle stand-in
GREEN = np.array([0.36, 0.66, 0.36])     # snake rear piece
ORANGE = np.array([0.93, 0.56, 0.20])    # snake front piece
RED = np.array([0.85, 0.15, 0.15])       # M5 side bolts
PURPLE = np.array([0.55, 0.30, 0.75])    # alignment tabs
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
                    ("snake front piece (head)", ORANGE), ("alignment tabs", PURPLE), ("M5 side bolts", RED),
                    ("heat-set insert", BRASS),
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
    SCREWS = " / ".join(sorted({b["screw"].split()[0] for p in BOLTS.values() for b in p}))
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
                          "Hardware: 2 x M4 x 25 socket head bolts + 2 x M4 hex nuts (clamp), Jack's centre screw,\n"
                          f"4 x M5 heat-set inserts (6.4 mm hole, 6 mm deep), 4 x {SCREWS} socket head cap screws,\n"
                          "blue (medium) thread locker for the clamp bolts.\n"
                          "Tools: soldering iron (inserts), 4 mm hex key (side bolts), 3 mm hex key (clamp).", W=sc.W))

    # ---- 1. heat-set inserts
    rb = BOLTS["rear"][0]; BX = rb["x"]; BY = rb["insert_top_y"]; BS_ = rb["surface_y"]   # left bolt of the rear piece
    sci = Scene([0.30, -0.90, -0.32], UP, np.array([BX - 55, BY - 20, -45]), np.array([BX + 55, BS_ + 25, 45]), res=0.1)
    r_near = rear.slice_plane([BX - 45, 0, 0], [1, 0, 0]).slice_plane([BX + 45, 0, 0], [-1, 0, 0])
    ins = cyl_y(3.2, BS_ + 6, BS_ + 12, BX, 0.0)
    img = sci.render([(r_near, GREEN), (ins, BRASS)], density=3.0)
    d = ImageDraw.Draw(img)
    arrow(d, sci.px([BX, BS_ + 5, 0])[0], sci.px([BX, BY + 1, 0])[0], brass, width=10)
    q = sci.px([BX + 3.2, BS_ + 9, 0])[0]
    d.text((q[0] + 60, q[1] - 20), "M5 heat-set insert", fill=(30, 30, 30), font=fb, anchor="lm")
    img = autocrop(img)
    panels.append(caption(img, 1, "Before you start: the four heat-set inserts (once)",
                          "Each snake piece has a round hole on its left and on its right side (4 in all).\n"
                          "At the bottom of each wide hole is a narrower one: press an insert into it with a\n"
                          "soldering iron (about 230 C for PA-CF/PC) until it is flush with the bottom of the\n"
                          "wide hole. Let them cool.", W=sc.W))

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

    # ---- 4 to 8: the snake
    bx = lambda p: BOLTS[p][0]["x"]
    bolt_pt = lambda p, side: [bx(p), (1 if side == "left" else -1) * (abs(BOLTS[p][0]["surface_y"]) + 1), 0]
    step([(rifle, DARK), (base, GREY), (moved(rear, 300), GREEN)], 4, "Slide the rear snake piece on over the muzzle",
         "Tails first. It slides along the handguard like a sleeve. Take anything bolted to the\n"
         "keymod slots or the rail off first (sight, bipod mount).",
         arrows=[((520, 380), g)])
    step([(rifle, DARK), (base, GREY), (rear, GREEN)], 5, "Bolt it on from the left and the right",
         "Push it back until a keymod hole shows through the round hole on each side. Screw in an\n"
         "M5 bolt on each side, push the piece back so the bolts touch the back end of their keymod\n"
         f"holes, and tighten them snug ({BOLTS['rear'][0]['screw'].split()[0]}, no thread locker). It can no longer move back.",
         marks=[(bolt_pt("rear", "right"), "M5 bolt (one each side)", (0, -70))])
    step([(rifle, DARK), (base, GREY), (rear, GREEN), (moved(front, 200), ORANGE)], 6, "Slide the head piece on",
         "The barrel and muzzle device pass through the hole in the head. Its four tabs slide into\n"
         "the four pockets in the rear piece (two on each side) and line the pieces up. Push it back\n"
         "until the inside of the head sits against the end of the handguard.",
         arrows=[((650, 500), o)])
    step([(rifle, DARK), (base, GREY), (rear, GREEN), (front, ORANGE)], 7, "Bolt the head piece on from the left and the right",
         "Screw in its two M5 bolts and tighten them snug. They sit at the front end of their keymod\n"
         "holes, so nothing can move forward; the head stops against the end of the handguard,\n"
         "and the tabs keep the two pieces lined up.",
         marks=[(bolt_pt("front", "right"), "M5 bolt (one each side)", (0, -70))])
    step([(rifle, DARK), (base, GREY), (moved(rear, 150), GREEN), (moved(front, 200), ORANGE)], 8,
         "To take it off: unbolt the head, pull it forward, then the rear piece",
         "Two bolts out (left and right), pull the head forward off the muzzle.\n"
         "Two more bolts out, pull the rear piece forward. Only a hex key is needed;\n"
         "the handguard stays on the rifle.",
         arrows=[((480, 620), o), ((250, 380), g)])

    # close-up: the joint, pulled apart a little, with the tabs coloured
    XJ = LOCK["joint_x"]
    tabs = []
    for t in TABS:
        b = trimesh.creation.box(extents=[TAB_L + 6.0, TAB_W, TAB_H])
        b.apply_translation([t["face_x"] - TAB_L / 2 + 3.0, 0, 0])
        b.apply_transform(trimesh.transformations.rotation_matrix(np.radians(t["theta"]), [-1, 0, 0]))
        b.apply_translation([0, t["y"] - np.sin(np.radians(t["theta"])) * 0, t["z"]])
        tabs.append(b)
    tabs = trimesh.util.concatenate(tabs)
    gapx = 30.0
    scj = Scene([0.30, -0.88, -0.36], UP, np.array([XJ - 70, -50, -50]), np.array([XJ + 70 + gapx, 50, 50]), res=0.1)
    rj = rear.slice_plane([XJ - 50, 0, 0], [1, 0, 0])
    fj = front.slice_plane([XJ + 60, 0, 0], [-1, 0, 0])
    img = scj.render([(rj, GREEN), (moved(fj, gapx), ORANGE), (moved(tabs, gapx), PURPLE)], density=3.0)
    img = autocrop(img)
    panels.append(caption(img, None, "Close-up: the joint, pulled apart (right side)",
                          "Four rectangular tabs on the head piece (two on each body) slide into four pockets\n"
                          "in the rear piece. They line the pieces up so the snake reads as one; the bolts hold them.", W=sc.W))

    # close-up: cut across a side bolt, looking from the muzzle
    fb_ = BOLTS["front"][0]; FX = fb_["x"]
    scb = Scene([-1, 0, 0], UP, np.array([FX, -62, -40]), np.array([FX, 62, 45]), res=0.06)
    cutx = lambda m: m.slice_plane([FX, 0, 0], [-1, 0, 0], cap=True).slice_plane([FX - 12, 0, 0], [1, 0, 0], cap=True)
    bolts3 = []
    for b in BOLTS["front"]:
        s_ = 1 if b["side"] == "left" else -1
        y_f = abs(b["insert_top_y"]); L = float(b["screw"].split("x")[1].split()[0])
        bolts3 += [cyl_y(2.5, s_ * (y_f - L) if s_ > 0 else -y_f, s_ * y_f if s_ > 0 else -(y_f - L), FX, 0.0),
                   cyl_y(4.25, y_f if s_ > 0 else -(y_f + 5), y_f + 5 if s_ > 0 else -y_f, FX, 0.0)]
    barrel = cyl_x(9.5, FX - 30, FX + 30)
    img = scb.render([(cutx(base), GREY), (cutx(front), ORANGE), (trimesh.util.concatenate(bolts3), RED), (barrel, DARK)], density=3.0)
    img = autocrop(img)
    panels.append(caption(img, None, "Close-up: across the head piece's bolts (from the muzzle)",
                          "Each bolt goes through a heat-set insert in the body; its tip ends in a keymod hole,\n"
                          "inside the handguard's side wall: it never touches the barrel (free float).", W=sc.W))

    panels.append(caption(end_view(base, rear), None, "Why it cannot fall off or spin",
                          "Looking down the barrel from the muzzle (rear piece only). The snake hugs the handguard\n"
                          "with a 0.35 mm gap, so it can only slide forward and back (the bolts stop that).\n"
                          "The rail and the flat sides stop it turning.", W=sc.W))

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
