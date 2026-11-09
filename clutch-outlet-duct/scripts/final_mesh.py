import numpy as np, trimesh, fast_simplification, gc, time
from skimage import measure
t=time.time()
W=np.load('W3.npy'); g=np.load('grid.npy'); lo=g[:3]; h=g[3]
v,f,_,_=measure.marching_cubes(W,0.0,allow_degenerate=False); del W; gc.collect()
v=v*h+lo+h/2
print('mc',len(f),time.time()-t,flush=True)
v2,f2=fast_simplification.simplify(v.astype(np.float32),f.astype(np.int32),target_count=1_200_000)
del v,f; gc.collect()
m=trimesh.Trimesh(v2,f2,process=True)
cc=m.split(only_watertight=False)
print('components',len(cc),sorted([len(c.faces) for c in cc])[-5:])
m=max(cc,key=lambda c:len(c.faces))
trimesh.repair.fix_normals(m)
print('watertight',m.is_watertight,'winding',m.is_winding_consistent,'volume',m.volume)
# back to original scan coordinates
A=np.load('pca_T.npy'); c=A[0]; vt=A[1:]
m.vertices=m.vertices@vt+c
if m.volume<0: m.invert()
m.export('duct_pca_check.ply')
np.save('final_v.npy',m.vertices); np.save('final_f.npy',m.faces)
print('done',time.time()-t,'vol',m.volume,'bounds',m.bounds)
