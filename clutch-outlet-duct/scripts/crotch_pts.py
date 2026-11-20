# Points on the large unscanned patch between box and tube (gets extra smoothing).
import numpy as np,trimesh
v=np.load('sdfs_v.npy');f=np.load('sdfs_f.npy');gd=np.load('sdfs_gapdist.npy')
far=gd>1.0
m=trimesh.Trimesh(v,f[far[f].all(1)],process=False)
big=max(m.split(only_watertight=False),key=lambda c:c.area)
np.save('crotch_pts.npy',trimesh.Trimesh(big.vertices,big.faces).sample(int(big.area*30)).astype(np.float32))
