import numpy as np, gc
from scipy import ndimage as ndi
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
shape=tuple(np.load('Fa.npy',mmap_mode='r').shape)
F=np.load('crotch_pts.npy'); idx=np.floor((F-lo)/h).astype(np.int32)
S=np.zeros(shape,bool); S[idx[:,0],idx[:,1],idx[:,2]]=True; del idx
D=ndi.distance_transform_edt(~S); del S; gc.collect()
np.multiply(D,h,out=D); wz=np.clip(1-(D-2.5)/2.0,0,1).astype(np.float16); del D; gc.collect()
w=np.load('wfill.npy').astype(np.float16)   # distance-to-scan ramp
np.save('wzone.npy',(w*wz).astype(np.float16)); print('ok')
