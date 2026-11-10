import numpy as np, time
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
t0=time.time()
P=np.load('outerP.npy'); N=np.load('outerN.npy')
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
S0=np.load('surf.npy',mmap_mode='r'); shape=S0.shape; del S0
idx=np.floor((P-lo)/h).astype(np.int32)
S=np.zeros(shape,bool); S[idx[:,0],idx[:,1],idx[:,2]]=True
D=ndi.distance_transform_edt(~S).astype(np.float32)*h; del S
print('edt',time.time()-t0,flush=True)
band=np.nonzero(D<1.6)
X=(np.stack(band,1).astype(np.float32)+0.5)*h+lo
print('band',len(X),flush=True)
tree=cKDTree(P)
sd=np.empty(len(X),np.float32)
B=2_000_000
for i in range(0,len(X),B):
    x=X[i:i+B]; dd,ii=tree.query(x,k=12,workers=4)
    w=np.exp(-(dd/0.5)**2); w/=w.sum(1,keepdims=True)+1e-12
    proj=np.einsum('nkj,nkj->nk',x[:,None,:]-P[ii],N[ii])
    sd[i:i+B]=(w*proj).sum(1)
print('kd',time.time()-t0,flush=True)
# sign outside band from coarse vote
fr=np.load('frac_coarse.npy'); gc=np.load('grid_coarse.npy')
sign=np.empty(shape,np.float32)
# upsample coarse frac by nearest in chunks along x
for i0 in range(0,shape[0],64):
    i1=min(shape[0],i0+64)
    ii,jj,kk=np.meshgrid(np.arange(i0,i1),np.arange(shape[1]),np.arange(shape[2]),indexing='ij')
    Xc=(np.stack([ii,jj,kk],0).astype(np.float32)+0.5)*h+lo[:,None,None,None]
    c=(Xc-gc[:3,None,None,None])/gc[3]-0.5
    f=ndi.map_coordinates(fr,c.reshape(3,-1),order=1).reshape(ii.shape)
    sign[i0:i1]=np.where(f>0.5,-1,1)
F=sign*D; del sign,D
F[band]=sd
np.save('sdf.npy',F)
print('done',time.time()-t0)
