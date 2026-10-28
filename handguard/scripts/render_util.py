"""Quick depth-shaded orthographic renders of a triangle soup (numpy only)."""
import numpy as np
from PIL import Image


def render(T, view, up, res=0.25, out=None, crop=None):
    """T: (n,3,3) triangles. view: direction camera looks along. Splat triangle
    centroids + vertices into a z-buffer and shade by normal."""
    view = np.asarray(view, float); view /= np.linalg.norm(view)
    up = np.asarray(up, float); up -= view * (up @ view); up /= np.linalg.norm(up)
    right = np.cross(view, up)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    shade = np.abs(n @ (-view * 0.6 + up * 0.5 + right * 0.3) / np.linalg.norm([0.6, 0.5, 0.3]))
    pts = np.concatenate([T.mean(1), T[:, 0], T[:, 1], T[:, 2]])
    sh = np.tile(shade, 4)
    u = pts @ right; v = pts @ up; d = pts @ view
    if crop is not None:
        k = (u >= crop[0]) & (u <= crop[1]) & (v >= crop[2]) & (v <= crop[3])
        u, v, d, sh = u[k], v[k], d[k], sh[k]
    u0, v0 = u.min(), v.min()
    W = int((u.max() - u0) / res) + 1; H = int((v.max() - v0) / res) + 1
    iu = ((u - u0) / res).astype(int); iv = (H - 1 - ((v - v0) / res).astype(int))
    idx = iv * W + iu
    order = np.argsort(-d)  # far first, near overwrite
    img = np.zeros(W * H, np.float32)
    img[idx[order]] = sh[order]
    img = img.reshape(H, W)
    im = Image.fromarray((np.clip(img, 0, 1) * 235 + 20 * (img > 0)).astype(np.uint8))
    if out:
        im.save(out)
    return im, (u0, v0, W, H)


def render_mesh(mesh, view, up, res=0.25, out=None, crop=None, n=4_000_000, light=(0.6, 0.5, 0.3)):
    """Orthographic, Lambert-shaded render of a trimesh by dense surface splatting."""
    import trimesh
    P, fi = trimesh.sample.sample_surface(mesh, n)
    nrm = mesh.face_normals[fi]
    view = np.asarray(view, float); view /= np.linalg.norm(view)
    up = np.asarray(up, float); up -= view * (up @ view); up /= np.linalg.norm(up)
    right = np.cross(view, up)
    L = -view * light[0] + up * light[1] + right * light[2]; L /= np.linalg.norm(L)
    facing = nrm @ -view > 0
    P, nrm = P[facing], nrm[facing]
    sh = 0.25 + 0.75 * np.clip(nrm @ L, 0, 1)
    u = P @ right; v = P @ up; d = P @ view
    if crop is not None:
        k = (u >= crop[0]) & (u <= crop[1]) & (v >= crop[2]) & (v <= crop[3])
        u, v, d, sh = u[k], v[k], d[k], sh[k]
    u0, v0 = u.min(), v.min()
    W = int((u.max() - u0) / res) + 1; H = int((v.max() - v0) / res) + 1
    iu = ((u - u0) / res).astype(int); iv = (H - 1 - ((v - v0) / res).astype(int))
    idx = iv * W + iu
    order = np.argsort(-d)
    img = np.full(W * H, 0.12, np.float32)
    img[idx[order]] = sh[order]
    im = Image.fromarray((np.clip(img.reshape(H, W), 0, 1) * 255).astype(np.uint8))
    if out:
        im.save(out)
    return im
