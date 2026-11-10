import numpy as np, time
from scipy import ndimage as ndi
from scipy.spatial.transform import Rotation as Rot
import os
P=np.load('P.npy').astype(np.float32)
if os.path.exists('cap_pts.npy'): P=np.r_[P,np.load('cap_pts.npy')]
g=np.load('grid.npy'); lo=g[:3]; H=0.7
hi=P.max(0)+6
shape=np.ceil((hi-lo)/H).astype(int)+1
# coarse grid centers
ii=np.indices(shape).reshape(3,-1).T.astype(np.float32)
C=lo+ (ii+0.5)*H; del ii
ctr=P.mean(0)
votes=np.zeros(len(C),np.uint8); nv=0
rots=[np.eye(3)]+list(Rot.random(11,random_state=1).as_matrix())
for k,R in enumerate(rots):
    t=time.time()
    Q=(P-ctr)@R.T; l2=Q.min(0)-4; sh=np.ceil((Q.max(0)+4-l2)/H).astype(int)+1
    S=np.zeros(sh,bool); idx=((Q-l2)/H).astype(np.int32); S[idx[:,0],idx[:,1],idx[:,2]]=True
    S=ndi.binary_dilation(S)
    vol=np.zeros(sh,np.uint8)
    for ax in range(3):
        St=np.moveaxis(S,ax,0); Rr=St.copy(); Rr[1:]&=~St[:-1]
        Cc=np.cumsum(Rr,axis=0,dtype=np.int16); tot=Cc[-1:]
        V=np.moveaxis(vol,ax,0); V+=(Cc&1).astype(np.uint8); V+=((tot-Cc)&1).astype(np.uint8)
    # sample at coarse grid centers
    qc=((C-ctr)@R.T-l2)/H; qi=np.floor(qc).astype(np.int32)
    ok=np.all((qi>=0)&(qi<sh),1)
    vv=np.zeros(len(C),np.uint8); vv[ok]=vol[qi[ok,0],qi[ok,1],qi[ok,2]]
    votes+=vv; nv+=6
    print(k,time.time()-t,flush=True)
frac=(votes/nv).reshape(shape).astype(np.float32)
np.save('frac_coarse.npy',frac); np.save('grid_coarse.npy',np.r_[lo,[H]])
