# Step 2b: rebuild the outer solid field from the cleaned, closed outer mesh (true signed distance) where it changed.
import numpy as np, json, time, trimesh
from scipy.spatial import cKDTree
from scipy import ndimage as ndi
t0=time.time()
p=json.load(open('end_params.json')); a=np.array(p['box_a'])
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
fo=np.load('end_fo.npy'); V=np.load('end_V0.npy'); Vc=np.load('end_Vclean.npy'); F=np.load('end_F.npy')
shp=np.array(fo.shape)
mc=trimesh.Trimesh(Vc,F,process=False); print('cleaned mesh watertight',mc.is_watertight,'area',round(mc.area))
S,fi=mc.sample(int(mc.area*130),return_index=True); SN=mc.face_normals[fi]
idx=np.floor((S-lo)/h).astype(int)-a; ok=np.all((idx>=0)&(idx<shp),1)
surf=np.zeros(fo.shape,bool); surf[idx[ok,0],idx[ok,1],idx[ok,2]]=True
dil=ndi.binary_dilation(surf,iterations=1); del surf
lab,_=ndi.label(~dil); outside=lab==lab[0,0,0]; inside=(~dil)&(~outside); del lab
print('inside %.1f cm3, ambiguous shell %.1f cm3'%(inside.sum()*h**3/1000,dil.sum()*h**3/1000),time.time()-t0,flush=True)
moved=np.linalg.norm(Vc-V,axis=1)>0.01; tv=np.where(moved)[0]
mark=np.ones(fo.shape,bool)
for Q in (V[tv],Vc[tv]):
    ix=np.floor((Q-lo)/h).astype(int)-a; k=np.all((ix>=0)&(ix<shp),1); mark[ix[k,0],ix[k,1],ix[k,2]]=False
D=ndi.distance_transform_edt(mark)*h; band=np.argwhere(D<20.0); fall=np.clip((20.0-D[band[:,0],band[:,1],band[:,2]])/6.0,0,1); del mark,D
Xb=(band+a+0.5)*h+lo; print('band voxels',len(band),time.time()-t0,flush=True)
# far from the surface a voxel-grid distance is enough (only the sign matters there); near it, use exact distances to the mesh samples
surf2=np.zeros(fo.shape,bool); surf2[idx[ok,0],idx[ok,1],idx[ok,2]]=True
Dg=ndi.distance_transform_edt(~surf2).astype(np.float32)*h; del surf2
bi=(band[:,0],band[:,1],band[:,2]); dg=Dg[bi]; ins=inside[bi]; out=outside[bi]
sgn=np.where(ins,-1.0,np.where(out,1.0,0.0)); val=sgn*dg
nearm=dg<1.6; xn=Xb[nearm]; print('near-surface voxels',int(nearm.sum()),time.time()-t0,flush=True)
tr=cKDTree(S); dn=np.empty(len(xn)); sn=np.empty(len(xn))
for i in range(0,len(xn),1_000_000):
    dd,ii=tr.query(xn[i:i+1_000_000],k=3,workers=-1)
    pl=np.einsum('nkj,nkj->nk',xn[i:i+1_000_000,None,:]-S[ii],SN[ii]).mean(1)      # distance to the local tangent plane: smooth, no sampling texture
    use=(dd[:,0]<1.0)&(np.abs(pl)<=dd[:,0]+0.05); dn[i:i+1_000_000]=np.where(use,np.abs(pl),dd[:,0]); sn[i:i+1_000_000]=np.sign(pl)
sn[sn==0]=1; s0=sgn[nearm]; val[nearm]=np.where(s0!=0,s0,sn)*dn
amb=(sgn==0)&~nearm; val[amb]=dg[amb]      # cannot happen in practice (ambiguous shell is within 1 voxel of the surface)
fo2=fo.copy(); cur=fo[bi]; fo2[bi]=cur+fall*(val-cur)
w=np.load('end_w.npy'); colb=np.load('end_colb.npy'); wh=np.clip((w-0.85)/0.15,0,1); fo2=fo2+wh*(colb-fo2)   # the collar itself stays exact
np.save('end_fo2.npy',fo2); print('done',time.time()-t0)
