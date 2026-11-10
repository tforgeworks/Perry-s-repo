import numpy as np, gc
from scipy import ndimage as ndi
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
shape=tuple(np.load('Fa.npy',mmap_mode='r').shape)
P=np.r_[np.load('P.npy'),np.load('fill_pts.npy')[:,:3]]; idx=np.floor((P-lo)/h).astype(np.int32); del P
S=np.zeros(shape,bool); S[idx[:,0],idx[:,1],idx[:,2]]=True; del idx
D=ndi.distance_transform_edt(~S); del S; gc.collect()
np.multiply(D,h,out=D); np.minimum(D,10,out=D)
np.save('dall.npy',D.astype(np.float16)); print('ok')
