import numpy as np,trimesh
v=np.load('sdfs_v.npy');f=np.load('sdfs_f.npy');gd=np.load('sdfs_gapdist.npy')
far=gd>1.0
m=trimesh.Trimesh(v,f[far[f].all(1)],process=False)
cs=[c for c in m.split(only_watertight=False) if c.area>300]
pts=np.concatenate([trimesh.Trimesh(c.vertices,c.faces).sample(int(c.area*40)) for c in cs])
old=np.load('cap_pts.npy')
np.save('cap_pts.npy',np.r_[old,pts.astype(np.float32)]); print(len(cs),[round(c.area) for c in cs],len(pts))
