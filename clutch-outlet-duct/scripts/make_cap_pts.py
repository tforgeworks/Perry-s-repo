# After the first fill pass: sample the surface the fill put across the rectangular mouth,
# so later fill passes treat the mouth as closed (it is opened again in the final build).
import numpy as np,trimesh
v=np.load('sdfs_v.npy');f=np.load('sdfs_f.npy');gd=np.load('sdfs_gapdist.npy')
far=gd>1.0
m=trimesh.Trimesh(v,f[far[f].all(1)],process=False)
cap=min(m.split(only_watertight=False),key=lambda c:np.linalg.norm(c.vertices.mean(0)-[-148.6,-10,-3.7]))
np.save('cap_pts.npy',trimesh.Trimesh(cap.vertices,cap.faces).sample(300000).astype(np.float32))
