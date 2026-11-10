import numpy as np,trimesh
v=np.load('sdfs_v.npy');f=np.load('sdfs_f.npy');gd=np.load('sdfs_gapdist.npy')
far=gd>1.0
m=trimesh.Trimesh(v,f[far[f].all(1)],process=False)
c0=np.load('endframe.npy')[0]
P=[];N=[]
for c in m.split(only_watertight=False):
    if c.area<100: continue
    ctr=c.vertices.mean(0)
    if np.linalg.norm(ctr-[-148.9,-9.4,-3.7])<15: print('skip mouth cap',round(c.area)); continue
    if np.linalg.norm(ctr-c0)<40: print('skip outlet',round(c.area)); continue
    cm=trimesh.Trimesh(c.vertices,c.faces)
    p,fi=cm.sample(int(c.area*30),return_index=True)
    P.append(p);N.append(cm.face_normals[fi]); print('fill',round(c.area),ctr.round(1))
P=np.concatenate(P);N=np.concatenate(N)
# sdfs mesh normals from marching cubes on SDF: check orientation vs outward (F increasing)
np.save('fill_pts.npy',np.c_[P,N].astype(np.float32))
