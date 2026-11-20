import numpy as np, trimesh, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
v=np.load('sdfs_v.npy');f=np.load('sdfs_f.npy')
P=np.load('P.npy')[::2]
d,_=cKDTree(P).query(v,workers=4)
np.save('sdfs_gapdist.npy',d)
far=d>1.0
m=trimesh.Trimesh(v,f,process=False)
sub=trimesh.Trimesh(v,f[far[f].all(1)],process=False)
cc=sub.split(only_watertight=False)
cc=sorted(cc,key=lambda c:-c.area)
for c in cc[:8]:
    ctr=c.vertices.mean(0); u,s,vt=np.linalg.svd(c.vertices-ctr,full_matrices=False)
    print('area',round(c.area),'ctr',ctr.round(1),'normal',vt[2].round(3),'flatness',(s[2]/np.sqrt(len(c.vertices))).round(2),'ext',(c.vertices.max(0)-c.vertices.min(0)).round(0))
