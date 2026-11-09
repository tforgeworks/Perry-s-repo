import numpy as np, trimesh
m=trimesh.load('scan_600k.ply'); c=m.vertices.mean(0)
u,s,vt=np.linalg.svd(m.vertices-c,full_matrices=False)
V=np.load('verts.npy'); N=np.load('vnorm.npy')
np.save('P.npy',((V-c)@vt.T).astype(np.float32)); np.save('PN.npy',(N@vt.T).astype(np.float32))
np.save('pca_T.npy',np.r_[c[None],vt])
