# Replace the scorched tube surface with the design-intent sweep in the outer fields.
import numpy as np, json, gc, time
from sweepeval import project, radius, lo_s, hi_s
t0=time.time()
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
E=np.load('sdf_s.npy',mmap_mode='r+'); Fa=np.load('Fa.npy',mmap_mode='r+'); DA=np.load('dall.npy',mmap_mode='r+')
Z=json.load(open('sweep_in.json'))
S_LO=lo_s+4; S_FULL1=Z['s1']-20; S_HI=Z['s1']
nrep=0
for x0 in range(0,E.shape[0],40):
    b=np.argwhere(np.abs(np.asarray(E[x0:x0+40]))<14); b[:,0]+=x0
    if len(b)==0: continue
    X=(b+0.5)*h+lo
    s,th,rho=project(X); th0=th
    zone=(s>S_LO)&(s<S_HI)&(rho<np.where(s>130,75,radius(np.clip(s,lo_s,hi_s),th0)+12))
    if not zone.any(): continue
    b=b[zone]; s=s[zone]; th=th[zone]; rho=rho[zone]
    fs=(rho-radius(s,th)).astype(np.float32)
    eo=E[b[:,0],b[:,1],b[:,2]]
    ws=np.clip((S_HI-s)/(S_HI-S_FULL1),0,1)*np.clip((s-S_LO)/4,0,1)
    ws=ws*np.where(s>130,np.clip((4-np.abs(eo-fs))/2,0,1),1.0)   # near the box: only the same (tube) surface; near the outlet: replace crushed areas too
    E[b[:,0],b[:,1],b[:,2]]=eo+ws*(fs-eo)
    fa=Fa[b[:,0],b[:,1],b[:,2]]
    Fa[b[:,0],b[:,1],b[:,2]]=fa+ws*(fs-fa)
    da=DA[b[:,0],b[:,1],b[:,2]].astype(np.float32)
    DA[b[:,0],b[:,1],b[:,2]]=(da*(1-ws)).astype(DA.dtype)
    nrep+=int((ws>0.5).sum())
print('replaced voxels',nrep,time.time()-t0)
E.flush(); Fa.flush(); DA.flush()
