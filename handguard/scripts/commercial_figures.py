"""Black-and-white figures and measurements for the commercial user manual (manual/commercial/).

Dimensioned orthographic views of the installed snake, drawings of each piece, cross-sections at
stations along the handguard for both versions (standard and bipod rail), and detail views (front
sight clearance with the sight measured on the scan, bipod rail bottom). All numbers come from the
final 3D files; they are written to manual/commercial/measurements.json for build_commercial_manual.js.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from matplotlib.patches import Circle, Polygon as MPoly  # noqa: E402
from PIL import ImageDraw, ImageFont  # noqa: E402

import assembly_guide as AG  # noqa: E402
import build_double_helix as D  # noqa: E402
import build_handguard as HG  # noqa: E402
import build_snake as BS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "manual", "commercial")
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
SERIF_B = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
FONT = ImageFont.truetype(SERIF, 30)
FONT_S = ImageFont.truetype(SERIF, 26)
LIGHT, MID, DARK, BLACK = (np.array([v, v, v]) for v in (0.88, 0.66, 0.48, 0.10))
AG.BG = (255, 255, 255)
plt.rcParams.update({"font.family": "serif", "font.serif": ["Liberation Serif", "Times New Roman"], "font.size": 10})
X_FRONT = HG.X_END            # front end of the handguard, from its rear face
STATIONS = [60.0, 130.0, 200.0, 265.2, 320.0, 365.0]


def load(name):
    p = os.path.join(ROOT, name)
    return trimesh.load(p, force="mesh")


def save(img, name, crop=True):
    img = (AG.autocrop(img, pad=20) if crop else img).convert("L")
    img.save(os.path.join(OUT, name))
    print(name, img.size)


# ---------------------------------------------------------------- dimension lines on renders
def arrowhead(d, tip, direction, size=16):
    direction = direction / np.linalg.norm(direction); n = np.array([-direction[1], direction[0]])
    d.polygon([tuple(tip), tuple(tip - direction * size + n * size * 0.35), tuple(tip - direction * size - n * size * 0.35)], fill=(0, 0, 0))


def dim(d, a, b, off, text, font=FONT, ext=True):
    """Dimension between image points a and b, drawn displaced by the image vector `off`."""
    a = np.asarray(a, float); b = np.asarray(b, float); off = np.asarray(off, float)
    a2, b2 = a + off, b + off
    if ext and np.linalg.norm(off) > 0:
        u = off / np.linalg.norm(off)
        for p, p2 in ((a, a2), (b, b2)):
            d.line([tuple(p + u * 6), tuple(p2 + u * 12)], fill=(0, 0, 0), width=2)
    d.line([tuple(a2), tuple(b2)], fill=(0, 0, 0), width=2)
    arrowhead(d, a2, a2 - b2); arrowhead(d, b2, b2 - a2)
    m = (a2 + b2) / 2
    box = d.textbbox(tuple(m), text, font=font, anchor="mm")
    d.rectangle([box[0] - 8, box[1] - 4, box[2] + 8, box[3] + 4], fill=(255, 255, 255))
    d.text(tuple(m), text, fill=(0, 0, 0), font=font, anchor="mm")


def note(d, sc, p, text, off, font=FONT_S, px=None):
    q = (px or sc.px)(p)[0]; t = q + np.array(off)
    d.line([tuple(t), tuple(q)], fill=(0, 0, 0), width=2)
    d.ellipse([q[0] - 5, q[1] - 5, q[0] + 5, q[1] + 5], fill=(0, 0, 0))
    anchor = "md" if off[1] < 0 else "ma"
    box = d.textbbox(tuple(t), text, font=font, anchor=anchor)
    d.rectangle([box[0] - 6, box[1] - 4, box[2] + 6, box[3] + 4], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    d.text(tuple(t), text, fill=(0, 0, 0), font=font, anchor=anchor)


def padded(sc_args, pad=180):
    """A Scene with room around the parts for dimensions."""
    view, up, lo, hi, res = sc_args
    sc = AG.Scene(view, up, np.asarray(lo, float), np.asarray(hi, float), res)
    return sc, pad


def render_padded(sc, items, pad):
    img = sc.render(items, density=3.0)
    from PIL import Image
    big = Image.new("RGB", (img.width + 2 * pad, img.height + 2 * pad), (255, 255, 255))
    big.paste(img, (pad, pad))
    px = lambda p: sc.px(p) + pad
    return big, px


# ---------------------------------------------------------------- sight measured on the scan
def scanned_sight():
    """Solid outline of the front sight from the scan (slice by slice), in its fitted position."""
    pts = np.load(os.path.join(ROOT, "work", "sight_pts.npy"))
    pts = pts[(pts[:, 0] > 308) & (pts[:, 0] < 374)]
    from manifold3d import Manifold, OpType
    boxes = []
    for x in np.arange(312, 370, 2.0):
        q = pts[(pts[:, 0] >= x) & (pts[:, 0] < x + 2)]
        if len(q) < 100:
            continue
        y0, y1 = np.percentile(q[:, 1], [0.3, 99.7]); z0, z1 = np.percentile(q[:, 2], [0.3, 99.7])
        boxes.append(Manifold.cube((2.0, y1 - y0, z1 - z0)).translate((x, y0, z0)))
    base = HG.build(json.load(open(os.path.join(ROOT, "data", "hole_templates.json"))))
    return HG.to_trimesh(Manifold.batch_boolean(boxes, OpType.Add) - base)


# ---------------------------------------------------------------- cross-sections
def section_polys(mesh, x):
    sec = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    if sec is None:
        return []
    P, _ = sec.to_2D(to_2D=np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -x], [0, 0, 0, 1]], float))
    return P.polygons_full


def draw_poly(ax, poly, face, hatch, lw=0.8):
    ext = np.asarray(poly.exterior.xy).T
    ax.add_patch(MPoly(ext, closed=True, facecolor=face, edgecolor="black", hatch=hatch, linewidth=lw))
    for r in poly.interiors:
        ax.add_patch(MPoly(np.asarray(r.xy).T, closed=True, facecolor="white", edgecolor="black", linewidth=lw))


def sections_figure(base, pieces, title, name, meas):
    fig, axs = plt.subplots(2, 3, figsize=(7.2, 6.6))
    rows = []
    for ax, x in zip(axs.flat, STATIONS):
        for p in section_polys(base, x):
            draw_poly(ax, p, "0.90", "////")
        sn = [p for m in pieces for p in section_polys(m, x)]
        for p in sn:
            draw_poly(ax, p, "0.45", None)
        ax.add_patch(Circle((0, 0), 9.5, facecolor="none", edgecolor="black", linestyle="--", linewidth=0.7))
        if sn:
            b = np.array([p.bounds for p in sn])
            y0, z0, y1, z1 = b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max()
            area = sum(p.area for p in sn)
            ax.annotate("", (y0, -50), (y1, -50), arrowprops=dict(arrowstyle="<->", lw=0.7))
            ax.text((y0 + y1) / 2, -53, f"{y1 - y0:.1f}", ha="center", va="top", fontsize=8,
                    bbox=dict(facecolor="white", edgecolor="none", pad=0.5))
            ax.annotate("", (52, z0), (52, z1), arrowprops=dict(arrowstyle="<->", lw=0.7))
            ax.text(55, (z0 + z1) / 2, f"{z1 - z0:.1f}", ha="left", va="center", fontsize=8, rotation=90)
            rows.append({"x": x, "from_front": round(X_FRONT - x, 1), "width": round(y1 - y0, 1), "height": round(z1 - z0, 1),
                         "z_min": round(z0, 1), "z_max": round(z1, 1), "area_mm2": round(area)})
        ax.set_title(f"Section at {x:.0f} mm\n({X_FRONT - x:.0f} mm from the front end)", fontsize=9)
        ax.set_xlim(-62, 66); ax.set_ylim(-64, 62); ax.set_aspect("equal")
        ax.set_xticks([-40, -20, 0, 20, 40]); ax.set_yticks([-40, -20, 0, 20, 40]); ax.tick_params(labelsize=7)
        ax.grid(color="0.85", linewidth=0.4)
    fig.suptitle(title, fontsize=11)
    fig.text(0.5, 0.01, "Viewed from the muzzle; rifle's left side on the right. Dark: snake. Hatched: handguard (not included). "
             "Dashed: barrel (reference, 19 mm). Dimensions in mm: overall width and height of the snake in each section.",
             ha="center", fontsize=7.5, wrap=True)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95), h_pad=1.6)
    fig.savefig(os.path.join(OUT, name), dpi=220); plt.close(fig)
    meas[name.replace(".png", "")] = rows
    print(name)


def main():
    os.makedirs(OUT, exist_ok=True)
    meas = {}
    base = load("handguard_base.stl")
    rear, front = load("snake_rear.3mf"), load("snake_front.3mf")
    snake = trimesh.util.concatenate([rear, front])
    lo, hi = snake.bounds
    L = json.load(open(os.path.join(ROOT, "data", "snake_lock.json")))
    meas["overall"] = {"length": round(hi[0] - lo[0], 1), "width": round(hi[1] - lo[1], 1), "height": round(hi[2] - lo[2], 1),
                       "x_rear": round(lo[0], 1), "x_front": round(hi[0], 1), "overhang": round(hi[0] - X_FRONT, 1),
                       "handguard_length": round(X_FRONT - 0.2, 1)}
    for nm, m in (("rear", rear), ("front", front), ("rear_bipod_rail", load("snake_rear_bipod_rail.3mf")),
                  ("front_bipod_rail", load("snake_front_bipod_rail.3mf"))):
        b0, b1 = m.bounds
        meas[nm] = {"length": round(b1[0] - b0[0], 1), "width": round(b1[1] - b0[1], 1), "height": round(b1[2] - b0[2], 1),
                    "x": [round(b0[0], 1), round(b1[0], 1)], "volume_cm3": round(m.volume / 1000, 1),
                    "mass_solid_g": round(m.volume / 1000 * 1.20), "area_cm2": round(m.area / 100)}

    # 1. cover / perspective
    sc = AG.Scene([-0.62, -0.58, -0.40], AG.UP, np.array([-5.0, -50, -50]), np.array([470.0, 50, 60]), res=0.28)
    save(sc.render([(base, LIGHT), (rear, MID), (front, MID)], density=3.0), "cover.png")

    # 2. exploded
    sc = AG.Scene([-0.62, -0.58, -0.40], AG.UP, np.array([-5.0, -50, -170]), np.array([640.0, 50, 60]), res=0.32)
    img = sc.render([(base, LIGHT), (AG.moved_z(AG.moved(rear, 60), -110), MID), (AG.moved_z(AG.moved(front, 150), -110), DARK)], density=3.0)
    d = ImageDraw.Draw(img)
    note(d, sc, [200, 0, 31], "Handguard (not included)", (0, -90))
    note(d, sc, [190, -30, -150], "A  Rear piece", (0, 110))
    note(d, sc, [470, -30, -150], "B  Head piece", (0, 110))
    save(img, "exploded.png")

    # 3. side view with overall dimensions (rifle's left side, muzzle to the left)
    sc = AG.Scene([0, -1, 0], AG.UP, np.array([-5.0, -50, -50]), np.array([470.0, 50, 60]), res=0.25)
    img, px = render_padded(sc, [(base, LIGHT), (rear, MID), (front, MID)], 200)
    d = ImageDraw.Draw(img)
    zb, zt = lo[2], hi[2]
    p = lambda x, z: px([x, 0, z])[0]
    dim(d, p(lo[0], zb), p(hi[0], zb), (0, 70), f"{hi[0] - lo[0]:.1f}  overall length of the snake")
    dim(d, p(0.2, zb), p(X_FRONT, zb), (0, 140), f"{X_FRONT - 0.2:.1f}  handguard (not included)")
    dim(d, p(X_FRONT, zt), p(hi[0], zt), (0, -60), f"{hi[0] - X_FRONT:.1f}  head")
    dim(d, p(L["joint_x"], zt), p(0.2, zt), (0, -60), f"{L['joint_x'] - 0.2:.1f}  joint, from the handguard's rear end")
    dim(d, p(hi[0], zb), p(hi[0], zt), (-80, 0), f"{zt - zb:.1f}")
    for k, lab in (("rear", "rear piece screw"), ("front", "head piece screw")):
        b = [q for q in L["bolts"][k] if q["side"] == "left"][0]
        q = px([b["x"], b["surface_y"], 0])[0]
        d.ellipse([q[0] - 7, q[1] - 7, q[0] + 7, q[1] + 7], outline=(0, 0, 0), width=3)
    save(img, "dims_side.png")
    meas["screw_x_from_rear"] = {k: round(L["bolts"][k][0]["x"] - 0.2, 1) for k in ("rear", "front")}
    meas["screw_x_from_front"] = {k: round(X_FRONT - L["bolts"][k][0]["x"], 1) for k in ("rear", "front")}

    # 4. top view with widths and the sight zone
    sight = scanned_sight()
    sc = AG.Scene([0, 0, -1], [0, -1, 0], np.array([-5.0, -50, -50]), np.array([470.0, 50, 60]), res=0.25)
    img, px = render_padded(sc, [(base, LIGHT), (rear, MID), (front, MID), (sight, BLACK)], 200)
    d = ImageDraw.Draw(img)
    # widest section of the snake along X
    best = (0, 0)
    for x in np.arange(lo[0] + 5, X_FRONT, 2.0):
        pl = section_polys(snake, x)
        if pl:
            b = np.array([q.bounds for q in pl]); w = b[:, 2].max() - b[:, 0].min()
            if w > best[0]:
                best = (w, x, b[:, 0].min(), b[:, 2].max())
    w, xw, y0, y1 = best
    dim(d, px([lo[0], lo[1], 60])[0], px([lo[0], hi[1], 60])[0], (90, 0), f"{hi[1] - lo[1]:.1f}")
    sx = D.SIGHT_CLAMP["x"]
    note(d, sc, [345, 0, 43], "front sight in the 2nd rail slot from the muzzle (customer's)", (300, -185), px=px)
    note(d, sc, [(sx[0] + sx[1]) / 2, D.SIGHT_CLAMP["half_w"] - 3, 25],
         f"necks trimmed for the sight clamp, {X_FRONT - sx[1]:.0f} to {X_FRONT - sx[0]:.0f} mm from the handguard's front end", (330, 185), px=px)
    save(img, "dims_top.png")
    meas["widest"] = {"width": round(w, 1), "x": round(xw, 1)}

    # 5. from the muzzle: width, height, barrel passage
    sc = AG.Scene([-1, 0, 0], AG.UP, np.array([380.0, -50, -50]), np.array([470.0, 50, 60]), res=0.07)
    img, px = render_padded(sc, [(base, LIGHT), (rear, MID), (front, MID)], 220)
    d = ImageDraw.Draw(img)
    pr = BS.PASSAGE_R
    dim(d, px([470, -pr, 0])[0], px([470, pr, 0])[0], (0, 0), f"\u00d8{2 * pr:.0f} barrel passage", ext=False)
    dim(d, px([470, lo[1], lo[2]])[0], px([470, hi[1], lo[2]])[0], (0, 110), f"{hi[1] - lo[1]:.1f}")
    dim(d, px([470, hi[1], lo[2]])[0], px([470, hi[1], hi[2]])[0], (110, 0), f"{hi[2] - lo[2]:.1f}")
    save(img, "dims_front.png")

    # 6. each piece, side view with its own size
    for nm, m, lab in (("rear", rear, "A  Rear piece (standard)"), ("front", front, "B  Head piece (standard)"),
                       ("rear_bipod_rail", load("snake_rear_bipod_rail.3mf"), "A  Rear piece (bipod rail)"),
                       ("front_bipod_rail", load("snake_front_bipod_rail.3mf"), "B  Head piece (bipod rail)")):
        b0, b1 = m.bounds
        sc = AG.Scene([0, -1, 0], AG.UP, b0 - 2, b1 + 2, res=0.2)
        img, px = render_padded(sc, [(m, MID)], 170)
        d = ImageDraw.Draw(img)
        dim(d, px([b0[0], 0, b0[2]])[0], px([b1[0], 0, b0[2]])[0], (0, 70), f"{b1[0] - b0[0]:.1f}")
        dim(d, px([b1[0], 0, b0[2]])[0], px([b1[0], 0, b1[2]])[0], (-70, 0), f"{b1[2] - b0[2]:.1f}")
        d.text((20, 20), lab, fill=(0, 0, 0), font=ImageFont.truetype(SERIF_B, 34))
        save(img, f"piece_{nm}.png")

    # 7. cross-sections, both versions
    sections_figure(base, [rear, front], "Cross-sections, standard version", "sections_standard.png", meas)
    sections_figure(base, [load("snake_rear_bipod_rail.3mf"), load("snake_front_bipod_rail.3mf")],
                    "Cross-sections, bipod rail version", "sections_bipod_rail.png", meas)

    # 8. front sight clearance detail: the sight from the scan in place, from above and from the front
    cut = lambda mm: mm.slice_plane([300, 0, 0], [1, 0, 0])
    sc = AG.Scene([0.30, -0.55, -0.78], AG.UP, np.array([300.0, -48, -30]), np.array([420.0, 48, 60]), res=0.09)
    img = sc.render([(cut(base), LIGHT), (cut(front), MID), (sight, BLACK)], density=3.0)
    d = ImageDraw.Draw(img)
    note(d, sc, [359, -17.6, 30], "sight clamp knob", (-200, -120))
    note(d, sc, [372, 20, 23], "trimmed: 2 mm or more clearance all round", (230, 160))
    save(img, "sight_detail.png")
    xs = 359.0
    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    for p in section_polys(base, xs):
        draw_poly(ax, p, "0.90", "////")
    for p in section_polys(front, xs):
        draw_poly(ax, p, "0.45", None)
    for p in section_polys(sight, xs):
        draw_poly(ax, p, "0.10", None)
    w, z0 = D.SIGHT_CLAMP["half_w"], D.SIGHT_CLAMP["z"]
    ax.plot([-w, -w, w, w], [62, z0, z0, 62], color="black", linestyle="--", linewidth=0.8)
    ax.annotate("", (-w, 58), (w, 58), arrowprops=dict(arrowstyle="<->", lw=0.7))
    ax.text(0, 59, f"trim {2 * w:.0f} mm wide", ha="center", va="bottom", fontsize=8)
    ax.annotate(f"trim from {z0:.1f} mm above the bore axis", (w, z0), (w + 3, 8), fontsize=7.5,
                arrowprops=dict(arrowstyle="-", lw=0.6))
    ax.set_xlim(-48, 62); ax.set_ylim(-10, 66); ax.set_aspect("equal"); ax.grid(color="0.85", linewidth=0.4)
    ax.set_title(f"Section through the sight clamp ({X_FRONT - xs:.0f} mm from the front end)", fontsize=9)
    fig.text(0.5, 0.02, "Black: front sight (measured on the scan). Dark grey: snake. Hatched: handguard and rail. "
             "Dashed: trimmed zone.", ha="center", fontsize=7)
    fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(os.path.join(OUT, "sight_section.png"), dpi=220); plt.close(fig)
    meas["sight"] = {"trim_x": [round(X_FRONT - sx[1], 1), round(X_FRONT - sx[0], 1)], "trim_width": 2 * w, "trim_z": z0}

    # 9. bipod rail version from below
    R = json.load(open(os.path.join(ROOT, "data", "bipod_rail.json")))
    (x0, x1), rw, zb = R["rail_x"], R["rail_half_width"], R["rail_bottom_z"]
    rail = trimesh.creation.box(extents=[x1 - x0, 2 * rw, -18.55 - zb]); rail.apply_translation([(x0 + x1) / 2, 0, (zb - 18.55) / 2])
    sc = AG.Scene([0, 0, 1], [0, 1, 0], np.array([-5.0, -50, -50]), np.array([470.0, 50, 60]), res=0.25)
    img, px = render_padded(sc, [(base, LIGHT), (load("snake_rear_bipod_rail.3mf"), MID), (load("snake_front_bipod_rail.3mf"), MID), (rail, BLACK)], 200)
    d = ImageDraw.Draw(img)
    note(d, sc, [(x0 + x1) / 2, 0, -40], "bottom accessory rail (customer's, not included)", (0, 170), px=px)
    note(d, sc, [150, -15, -40], f"snake cut level, {R['cut_z'] + 18.55:.1f} mm above the handguard's bottom face", (0, 170), px=px)
    save(img, "bipod_bottom.png")
    meas["bipod_rail"] = {"cut_above_bottom_face": round(R["cut_z"] + 18.55, 1), "rail_length": round(x1 - x0, 1)}
    json.dump(meas, open(os.path.join(OUT, "measurements.json"), "w"), indent=1)
    print(json.dumps(meas, indent=1)[:3000])


if __name__ == "__main__":
    main()
