# Remove scan-noise specks that stick out past the outer skin, and bring thin wall spots up to a 2.2 mm minimum.
import numpy as np, json, gc, sys
KEEP_SPECKS='--keep-specks' in sys.argv
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
W=np.load('W4.npy'); g=np.load('grid.npy'); lo=g[:3]; h=g[3]
lab=np.load('thin_lab.npy')
E=np.pad(np.load('sdf_s.npy'),((0,W.shape[0]-np.load('sdf_s.npy',mmap_mode='r').shape[0]),(0,0),(0,0)),constant_values=5.0)
p=json.load(open('params.json')); cc=np.array(p['cuff_center']); T=np.array(p['cuff_axis'])
sz=np.bincount(lab.ravel())
objs=ndi.find_objects(lab)
cap=cKDTree(np.load('cap_pts.npy')[:300000])
removed=0; thick=0
for k,sl in enumerate(objs,start=1):
    if sl is None: continue
    m=lab[sl]==k
    idx=np.argwhere(m)+np.array([s.start for s in sl]); X=(idx+0.5)*h+lo
    v=X-cc; d=v@T; rr=np.linalg.norm(v-np.outer(d,T),axis=1)
    if np.mean((rr<46)&(d>p['d0']-5))>0.3: continue          # new cuff, rim and tab: leave alone
    e=E[idx[:,0],idx[:,1],idx[:,2]]
    if sz[k]<2000:
        if not KEEP_SPECKS and np.mean(e>0.5)>0.5:                                # sticks out past the outer skin -> noise speck
            W[idx[:,0],idx[:,1],idx[:,2]]=np.maximum(W[idx[:,0],idx[:,1],idx[:,2]],0.05); removed+=1
    else:
        # thin wall patch: add a 2.2 mm shell inward from the outer skin around it, away from the mouth opening
        pad=12; a=np.maximum(idx.min(0)-pad,0); b=np.minimum(idx.max(0)+pad+1,W.shape)
        sub=(slice(a[0],b[0]),slice(a[1],b[1]),slice(a[2],b[2]))
        near=np.zeros(b-a,bool); near[tuple((idx-a).T)]=True; near=ndi.binary_dilation(near,iterations=pad)
        jj=np.argwhere(near)+a; Xj=(jj+0.5)*h+lo
        dc,_=cap.query(Xj,workers=4); ok=dc>4.0; jj=jj[ok]
        Ej=E[jj[:,0],jj[:,1],jj[:,2]]
        shell=np.maximum(Ej,-Ej-2.2)
        W[jj[:,0],jj[:,1],jj[:,2]]=np.minimum(W[jj[:,0],jj[:,1],jj[:,2]],shell); thick+=1
print('specks removed',removed,'thin patches thickened',thick)
np.save('W6.npy' if KEEP_SPECKS else 'W5.npy',W)
