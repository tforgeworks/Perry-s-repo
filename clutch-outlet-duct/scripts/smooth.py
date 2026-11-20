import numpy as np, time, gc
from scipy import ndimage as ndi
t=time.time()
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
shape=np.load('sdf.npy',mmap_mode='r').shape
P=np.load('outerP.npy')
idx=np.floor((P-lo)/h).astype(np.int32); del P
S=np.zeros(shape,bool); S[idx[:,0],idx[:,1],idx[:,2]]=True; del idx
D=ndi.distance_transform_edt(~S,return_distances=True); del S; gc.collect()
w=np.clip((D*h-0.4)/1.0,0,1).astype(np.float32); del D; gc.collect()
np.save('w.npy',w); del w; gc.collect()
print('edt',time.time()-t,flush=True)
F=np.load('sdf.npy'); np.clip(F,-6,6,out=F)
Fh=ndi.gaussian_filter(F,2.5/h); np.save('Fh.npy',Fh); del Fh; gc.collect()
Fs=ndi.gaussian_filter(F,0.5/h); del F; gc.collect()
Fh=np.load('Fh.npy'); Fh-=Fs; w=np.load('w.npy'); Fh*=w; del w; Fs+=Fh; del Fh
np.save('sdf_s.npy',Fs); print('done',time.time()-t)
