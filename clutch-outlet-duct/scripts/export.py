import numpy as np, trimesh, fast_simplification, pymeshfix, json
v=np.load('final_v.npy'); f=np.load('final_f.npy')
v2,f2=fast_simplification.simplify(v.astype(np.float32),f.astype(np.int32),target_count=800_000)
mf=pymeshfix.MeshFix(v2.astype(np.float64),f2.astype(np.int32)); mf.repair()
m=trimesh.Trimesh(mf.points if hasattr(mf,"points") else mf.v, mf.faces if hasattr(mf,"faces") else mf.f,process=True)
if m.volume<0: m.invert()
e=m.edges_sorted; u,c=np.unique(e,axis=0,return_counts=True)
print('faces',len(m.faces),'watertight',m.is_watertight,'winding',m.is_winding_consistent,'boundary',(c==1).sum(),'nonmanifold',(c>2).sum(),'bodies',m.body_count,'volume mm3',round(m.volume))
m.export('final_export.stl')
# compare with pre-decimation surface
from scipy.spatial import cKDTree
S=np.load('final_samples.npy')[:,:3]; A=np.load('pca_T.npy')
q=(m.sample(500000)-A[0])@A[1:].T
d,_=cKDTree(S).query(q,workers=4); print('decimation deviation median/p99/max',np.median(d).round(3),np.percentile(d,99).round(3),d.max().round(3))
