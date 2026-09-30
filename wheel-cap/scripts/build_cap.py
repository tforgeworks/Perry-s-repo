"""Build a clean, symmetric, printable STL of the CAP5372-61397 center cap from its 3D scan.

Pipeline:
  1. align     axis from PCA and flat faces, cap front up, clips down
  2. center    D6 symmetry center and mirror axis fitted on a top-view thickness map
  3. voxelize  exact column rasterization (fractional occupancy along z) at --res mm,
               done once per D6 group element (6 rotations x 2 mirrors) and averaged
  4. mesh      light Gaussian blur, marching cubes at 0.5, Taubin smoothing, decimation
  5. export    lowest point at z=0, watertight check

Usage: python build_cap.py work/Mesh_Gene.stl --out wheel_cap_CAP5372.stl --work work
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage, optimize
from skimage import measure

T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------- rasterizer

def rasterize(V, F, grid, flip=False):
    """Fractional occupancy of a closed, outward-oriented mesh on a voxel grid.

    For every column (x_i, y_j) the ray along z is intersected with all triangles.
    A crossing at height zc with facing s = sign(n_z) adds s to every voxel below zc
    and s * fraction to the voxel containing zc. For a closed mesh this is the exact
    inside length of each voxel along z, divided by the voxel height.
    """
    x0, y0, z0, h, nx, ny, nz = (grid[k] for k in ("x0", "y0", "z0", "h", "nx", "ny", "nz"))
    tri = V[F]
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    area2 = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    ok = np.abs(area2) > 1e-14
    a, b, c, area2 = a[ok], b[ok], c[ok], area2[ok]
    lo = np.minimum(np.minimum(a, b), c)
    hi = np.maximum(np.maximum(a, b), c)
    i0 = np.ceil((lo[:, 0] - x0) / h).astype(np.int64)
    i1 = np.floor((hi[:, 0] - x0) / h).astype(np.int64)
    j0 = np.ceil((lo[:, 1] - y0) / h).astype(np.int64)
    j1 = np.floor((hi[:, 1] - y0) / h).astype(np.int64)
    ni = np.clip(i1 - i0 + 1, 0, None)
    nj = np.clip(j1 - j0 + 1, 0, None)
    cnt = ni * nj
    has = np.nonzero(cnt)[0]

    cols, ks, fr, ss = [], [], [], []
    chunk = 400_000
    for s0 in range(0, len(has), chunk):
        t = has[s0:s0 + chunk]
        n = cnt[t]
        rep = np.repeat(np.arange(len(t)), n)
        off = np.arange(rep.size) - np.repeat(np.cumsum(n) - n, n)
        tt = t[rep]
        ii = i0[tt] + off // nj[tt]
        jj = j0[tt] + off % nj[tt]
        px = x0 + ii * h
        py = y0 + jj * h
        A, B, C, ar = a[tt], b[tt], c[tt], area2[tt]
        w0 = ((B[:, 0] - px) * (C[:, 1] - py) - (B[:, 1] - py) * (C[:, 0] - px)) / ar
        w1 = ((C[:, 0] - px) * (A[:, 1] - py) - (C[:, 1] - py) * (A[:, 0] - px)) / ar
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0) & (ii >= 0) & (ii < nx) & (jj >= 0) & (jj < ny)
        zc = (w0 * A[:, 2] + w1 * B[:, 2] + w2 * C[:, 2])[inside]
        s = np.sign(ar[inside])
        if flip:
            s = -s
        u = (zc - z0) / h
        k = np.floor(u).astype(np.int64)
        f = u - k
        below = k < 0
        above = k >= nz
        k = np.clip(k, 0, nz)
        f = np.where(above, 0.0, f)
        keep = ~below
        cols.append((ii[inside] * ny + jj[inside])[keep])
        ks.append(k[keep])
        fr.append(f[keep])
        ss.append(s[keep])
    col = np.concatenate(cols)
    k = np.concatenate(ks)
    f = np.concatenate(fr)
    s = np.concatenate(ss)
    idx = col * (nz + 1) + k
    size = nx * ny * (nz + 1)
    Bc = np.bincount(idx, weights=s, minlength=size).astype(np.float32).reshape(nx, ny, nz + 1)
    occ = np.bincount(idx, weights=s * f, minlength=size).astype(np.float32).reshape(nx, ny, nz + 1)
    # voxel k gets s from every crossing with index > k
    Bc = np.cumsum(Bc[..., ::-1], axis=2)[..., ::-1]
    occ[..., :nz] += Bc[..., 1:]
    occ = occ[..., :nz]
    np.clip(occ, 0.0, 1.0, out=occ)
    return occ


def make_grid(bounds, h, pad=3):
    lo = np.asarray(bounds[0]) - pad * h
    hi = np.asarray(bounds[1]) + pad * h
    # symmetric in xy about the origin so every D6 image lands on the same grid
    r = max(abs(lo[0]), abs(lo[1]), abs(hi[0]), abs(hi[1]))
    n = int(np.ceil(2 * r / h)) + 1
    jitter = 1.234567e-4 * h
    nz = int(np.ceil((hi[2] - lo[2]) / h)) + 1
    return dict(x0=-(n - 1) / 2 * h + jitter, y0=-(n - 1) / 2 * h + 0.7654321 * jitter,
                z0=lo[2], h=h, nx=n, ny=n, nz=nz)


# ---------------------------------------------------------------- alignment

def rot_z(t):
    c, s = np.cos(t), np.sin(t)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def frame_from_axis(z):
    z = z / np.linalg.norm(z)
    x = np.cross([0, 1.0, 0], z) if abs(z[1]) < 0.9 else np.cross([1.0, 0, 0], z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.stack([x, y, z])  # rows: new axes


def align_axis(m):
    """Rotation R and center c so that R @ (v - c) has the cap axis on z, front up."""
    w = m.area_faces
    ctr = (m.triangles_center * w[:, None]).sum(0) / w.sum()
    X = m.triangles_center - ctr
    cov = (X * w[:, None]).T @ X / w.sum()
    ev, evec = np.linalg.eigh(cov)
    z = evec[:, 0]
    # refine with the flat faces, which are all perpendicular to the axis
    for thr in (0.95, 0.99, 0.998):
        d = m.face_normals @ z
        sel = np.abs(d) > thr
        n = m.face_normals[sel] * np.sign(d[sel])[:, None]
        z = (n * w[sel, None]).sum(0)
        z /= np.linalg.norm(z)
    R = frame_from_axis(z)
    V = (m.vertices - ctr) @ R.T
    # the snap clips hang far below the widest ring (bolt tabs); the dome above is short
    zz = V[:, 2]
    rr = np.hypot(V[:, 0], V[:, 1])
    zw = np.median(zz[rr > np.percentile(rr, 99.5)])
    if (zz.max() - zw) > (zw - zz.min()):
        R = np.diag([1.0, -1.0, -1.0]) @ R
    return R, ctr


def fit_symmetry(V, F, h=0.3, span=60.0):
    """Fit the D6 center and mirror axis on a top-view thickness map."""
    grid = make_grid((V.min(0), V.max(0)), h, pad=6)
    T = rasterize(V, F, grid).sum(axis=2) * h
    n = grid["nx"]
    coords = grid["x0"] + np.arange(n) * h
    X, Y = np.meshgrid(coords, coords, indexing="ij")
    msk = T > 0.05 * T.max()
    px, py = X[msk], Y[msk]

    def sample(qx, qy):
        return ndimage.map_coordinates(T, [(qx - grid["x0"]) / h, (qy - grid["y0"]) / h],
                                       order=1, mode="constant")

    base = sample(px, py)

    def cost_rot(c):
        tot = 0.0
        for k in range(1, 6):
            t = k * np.pi / 3
            dx, dy = px - c[0], py - c[1]
            qx = c[0] + np.cos(t) * dx - np.sin(t) * dy
            qy = c[1] + np.sin(t) * dx + np.cos(t) * dy
            tot += np.mean((sample(qx, qy) - base) ** 2)
        return tot

    c0 = np.array([(T * X).sum(), (T * Y).sum()]) / T.sum()
    res = optimize.minimize(cost_rot, c0, method="Nelder-Mead",
                            options=dict(xatol=1e-4, fatol=1e-10, initial_simplex=[c0, c0 + [0.5, 0], c0 + [0, 0.5]]))
    c = res.x

    def cost_mir(phi):
        dx, dy = px - c[0], py - c[1]
        c2, s2 = np.cos(2 * phi), np.sin(2 * phi)
        qx = c[0] + c2 * dx + s2 * dy
        qy = c[1] + s2 * dx - c2 * dy
        return np.mean((sample(qx, qy) - base) ** 2)

    phis = np.radians(np.arange(-span / 2, span / 2, 0.25) if span < 60 else np.arange(0, 60, 0.5))
    costs = [cost_mir(p) for p in phis]
    p0 = phis[int(np.argmin(costs))]
    r2 = optimize.minimize_scalar(cost_mir, bounds=(p0 - np.radians(1), p0 + np.radians(1)), method="bounded",
                                  options=dict(xatol=1e-6))
    rms0 = np.sqrt(np.mean(base ** 2))
    return c, r2.x, dict(rot_rel_rms=float(np.sqrt(res.fun / 5) / rms0),
                         mirror_rel_rms=float(np.sqrt(r2.fun) / rms0))


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scan")
    ap.add_argument("--out", default="wheel_cap_CAP5372.stl")
    ap.add_argument("--work", default="work")
    ap.add_argument("--res", type=float, default=0.15, help="voxel size in mm")
    ap.add_argument("--blur", type=float, default=0.6, help="Gaussian sigma in voxels")
    ap.add_argument("--taubin", type=int, default=10)
    ap.add_argument("--faces", type=int, default=400_000)
    ap.add_argument("--flip", action="store_true", help="flip the front/back decision")
    args = ap.parse_args()
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    info = {}

    m = trimesh.load(args.scan, force="mesh", process=True)
    m.merge_vertices()
    log(f"scan: {len(m.faces)} faces, watertight={m.is_watertight}, volume={m.volume:.1f}")
    if m.volume < 0:
        m.invert()
    info["scan"] = dict(faces=int(len(m.faces)), watertight=bool(m.is_watertight), volume=float(m.volume))

    R, ctr = align_axis(m)
    if args.flip:
        R = np.diag([1.0, -1.0, -1.0]) @ R
    V = (m.vertices - ctr) @ R.T
    F = m.faces
    c, phi, sym = fit_symmetry(V, F)
    log(f"symmetry center offset {c}, mirror axis {np.degrees(phi):.3f} deg, residuals {sym}")
    # second pass at the fitted center for a finer estimate
    V = V - [c[0], c[1], 0]
    V = V @ rot_z(-phi).T
    c2, phi2, sym = fit_symmetry(V, F, h=0.2, span=4.0)
    V = (V - [c2[0], c2[1], 0]) @ rot_z(-phi2).T
    log(f"refined: offset {c2}, angle {np.degrees(phi2):.4f} deg, residuals {sym}")
    info["symmetry_fit"] = sym

    # full transform: aligned = Rt @ v + t
    Rt = rot_z(-phi2) @ rot_z(-phi) @ R
    t = -(rot_z(-phi2) @ (rot_z(-phi) @ (R @ ctr) + [c[0], c[1], 0]) + [c2[0], c2[1], 0])
    V = m.vertices @ Rt.T + t

    # ---- D6 average
    h = args.res
    grid = make_grid((V.min(0), V.max(0)), h, pad=4)
    log(f"grid {grid['nx']}x{grid['ny']}x{grid['nz']} at {h} mm")
    acc = np.zeros((grid["nx"], grid["ny"], grid["nz"]), np.float32)
    for mirror in (False, True):
        Vm = V * [1, -1, 1] if mirror else V
        for k in range(6):
            Vk = Vm @ rot_z(k * np.pi / 3).T
            acc += rasterize(Vk, F, grid, flip=mirror)
            log(f"  rasterized mirror={mirror} rot={60 * k}")
    acc /= 12.0
    if args.blur > 0:
        acc = ndimage.gaussian_filter(acc, args.blur)
    # drop loose specks (anything under ~1 mm3) before meshing
    lab, n = ndimage.label(acc > 0.5)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    small = sz < 1.0 / h ** 3
    small[0] = False
    if small[1:].any():
        acc[ndimage.binary_dilation(small[lab], iterations=2) & ~ndimage.binary_dilation(~small[lab] & (lab > 0), iterations=2)] = 0
    log(f"field components: {n}, removed specks: {int(small[1:].sum())}")

    # values sitting exactly on the iso level put vertices on grid corners and
    # produce non-manifold edges; nudge them off the level
    acc[np.abs(acc - 0.5) < 1e-4] = 0.5 + 1e-4
    verts, faces, _, _ = measure.marching_cubes(acc, 0.5, spacing=(h, h, h))
    del acc
    verts += [grid["x0"], grid["y0"], grid["z0"] + h / 2]
    out = trimesh.Trimesh(verts, faces, process=True)
    if out.volume < 0:
        out.invert()
    log(f"marching cubes: {len(out.faces)} faces, volume {out.volume:.1f}")
    trimesh.smoothing.filter_taubin(out, lamb=0.5, nu=-0.53, iterations=args.taubin)
    if len(out.faces) > args.faces:
        import fast_simplification
        p2, f2 = fast_simplification.simplify(out.vertices, out.faces, 1 - args.faces / len(out.faces))
        out = trimesh.Trimesh(p2, f2, process=True)
    out.merge_vertices()
    out.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(out)
    log(f"final: {len(out.faces)} faces, watertight={out.is_watertight}, volume={out.volume:.1f}")
    if not out.is_watertight:
        trimesh.repair.fill_holes(out)
        log(f"after hole fill watertight={out.is_watertight}")

    dz = -out.vertices[:, 2].min()
    out.apply_translation([0, 0, dz])
    t = t + [0, 0, dz]
    out.export(args.out)

    scan_al = trimesh.Trimesh(m.vertices @ Rt.T + t, m.faces, process=False)
    scan_al.export(work / "scan_aligned.stl")
    info.update(transform=dict(R=Rt.tolist(), t=list(map(float, t))),
                res=h, blur=args.blur, taubin=args.taubin,
                output=dict(faces=int(len(out.faces)), watertight=bool(out.is_watertight),
                            volume=float(out.volume), extents=list(map(float, out.extents))))
    Path(args.out).with_suffix(".build.json").write_text(json.dumps(info, indent=2))
    log(f"wrote {args.out} and {work / 'scan_aligned.stl'}")


if __name__ == "__main__":
    main()
