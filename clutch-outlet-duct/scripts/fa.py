import numpy as np, time, gc
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
t0=time.time()
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
shape=tuple(np.load('sdf_s.npy',mmap_mode='r').shape)
P=np.load('P.npy'); N=np.load('PN.npy')
A=np.load('fill_pts.npy')
P=np.r_[P,A[:,:3]]; N=np.r_[N,A[:,3:]]
idx=np.floor((P-lo)/h).astype(np.int32)
S=np.zeros(shape,bool); S[idx[:,0],idx[:,1],idx[:,2]]=True; del idx
D=ndi.distance_transform_edt(~S); del S; gc.collect()
band=np.nonzero(D*h<4.0); del D; gc.collect()
band=np.stack(band,1).astype(np.int32)
print('band',len(band),time.time()-t0,flush=True)
tree=cKDTree(P)
Fa=np.full(shape,5.0,np.float32)
B=1_500_000
for i in range(0,len(band),B):
    bi=band[i:i+B]; x=(bi+0.5)*h+lo
    dd,ii=tree.query(x,k=16,workers=4)
    n0=N[ii[:,0]]
    nn=N[ii]
    agree=np.einsum('nkj,nj->nk',nn,n0)>0.3
    w=np.exp(-(dd/0.6)**2)*agree; w[:,0]=np.maximum(w[:,0],1e-6)
    w/=w.sum(1,keepdims=True)
    proj=np.einsum('nkj,nkj->nk',x[:,None,:]-P[ii],nn)
    Fa[bi[:,0],bi[:,1],bi[:,2]]=(w*proj).sum(1)
    if i% (B*5)==0: print(i,time.time()-t0,flush=True)
np.save('Fa.npy',Fa); print('done',time.time()-t0)
