# Corrected outlet end, step 1: outer solid field in a local box.
#   tube (s >= 68): design-intent sweep (same as the revised model)
#   elbow / dome (s < 62): scan-derived outer surface
#   collar: ideal round collar with a lip (bead) on the measured axis, blended in above the junction
import numpy as np, json, time
from sweepeval import project, radius, ss, Lc
t0=time.time()
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
Eo=np.load('sdf_s_orig.npy',mmap_mode='r'); Es=np.load('sdf_s.npy',mmap_mode='r')
z=np.load('collar_frame.npz'); A=z['A']; c=z['c']; e1=z['e1']; e2=z['e2']
PAR=dict(seal_vox=12,open_r=2.1,close_r=1.4,plug_low=1.0,R=33.0,R_in=29.5,d_rim=24.0,bead_out=0.9,bead_h=4.5,d_a=3.0,d_b=9.0,zone_r=16.0,s_blend0=62.0,s_blend1=68.0,t_wall=2.5)
# local box: sweep centerline s in [15,125] padded by 60 mm, plus the collar
pts=np.r_[Lc[(ss>15)&(ss<125)],[c+A*20,c-A*70]]
bmin=pts.min(0)-62; bmax=pts.max(0)+62
a=np.maximum(np.floor((bmin-lo)/h).astype(int),0); b=np.minimum(np.ceil((bmax-lo)/h).astype(int),Eo.shape)
print('box',a,b,'shape',b-a)
E0=np.asarray(Eo[a[0]:b[0],a[1]:b[1],a[2]:b[2]]).copy(); E1_=np.asarray(Es[a[0]:b[0],a[1]:b[1],a[2]:b[2]])
# sweep where s>=68, scan envelope where s<62 (only voxels where the two differ need s)
diff=np.argwhere(np.abs(E1_-E0)>1e-4)
fo=E0.copy()
for i in range(0,len(diff),2_000_000):
    q=diff[i:i+2_000_000]; X=(q+a+0.5)*h+lo
    s,th,rho=project(X)
    w=np.clip((s-PAR['s_blend0'])/(PAR['s_blend1']-PAR['s_blend0']),0,1); w=w*w*(3-2*w)
    fo[q[:,0],q[:,1],q[:,2]]=E0[q[:,0],q[:,1],q[:,2]]+w*(E1_[q[:,0],q[:,1],q[:,2]]-E0[q[:,0],q[:,1],q[:,2]])
print('sweep blend',len(diff),time.time()-t0,flush=True)
del E1_
FO2=fo.copy()
# collar frame coordinates on the box
R=PAR['R']; drim=PAR['d_rim']
D=np.empty(fo.shape,np.float32); RAD=np.empty(fo.shape,np.float32)
xs=[(np.arange(a[i],b[i])+0.5)*h+lo[i] for i in range(3)]
for i0 in range(0,fo.shape[0],32):
    X=np.stack(np.meshgrid(xs[0][i0:i0+32],xs[1],xs[2],indexing='ij'),-1)-c
    d=X@A; D[i0:i0+32]=d; RAD[i0:i0+32]=np.linalg.norm(X-d[...,None]*A,axis=-1)
# mirror completion: the elbow is symmetric about the plane through the collar axis and the tube
# (fitted on intact overlaps: median mismatch 0.56 mm). Union the solid with its mirror image so the
# intact half restores the wall that burned away on the other half.
from scipy import ndimage as ndi
mp=np.load('mirror_plane.npz'); mm=mp['m']; moff=float(mp['off'])
i66=np.abs(ss-66).argmin(); o66=Lc[i66]; from sweepeval import Tc; t66=Tc[i66]/np.linalg.norm(Tc[i66])
for i0 in range(0,fo.shape[0],16):
    X=np.stack(np.meshgrid(xs[0][i0:i0+16],xs[1],xs[2],indexing='ij'),-1)
    wsym=np.clip((78-np.linalg.norm(X-c,axis=-1))/12,0,1)*np.clip(-((X-o66)@t66)/6,0,1)
    if not (wsym>0).any(): continue
    Xm=X-2*((X-c)@mm-moff)[...,None]*mm
    src=((Xm-lo)/h-0.5-a).reshape(-1,3).T
    fm=ndi.map_coordinates(fo,src,order=1,mode='constant',cval=5.0).reshape(wsym.shape)
    fo_new=np.minimum(fo[i0:i0+16],fm)
    FO2[i0:i0+16]=fo[i0:i0+16]+wsym*(fo_new-fo[i0:i0+16])
fo=FO2; del FO2
# plug: the scan also captured the inside of the opening and a pushed-in, melted wall on the far side.
# Fill the collar's own cylinder (and below it, to d = -22) so the outer solid has no pocket there.
plug=np.maximum(np.maximum(RAD-(R-0.3),D-drim),PAR['plug_low']-D)
fo=np.minimum(fo,plug)
# ideal collar solid with a rounded lip at the rim
# lip: a rounded-rectangle bead in the (radius, axial) profile, smoothly joined to the collar wall
bh=PAR['bead_h']/2; bw=(PAR['bead_out']+1.5)/2; rr_=1.4
qr=np.abs(RAD-(R+PAR['bead_out']-bw))-(bw-rr_); qd=np.abs(D-(drim-bh))-(bh-rr_)
bead=np.sqrt(np.maximum(qr,0)**2+np.maximum(qd,0)**2)+np.minimum(np.maximum(qr,qd),0)-rr_
col=RAD-R
k=2.0; hh=np.clip(0.5+0.5*(bead-col)/k,0,1); colb=bead*(1-hh)+col*hh-k*hh*(1-hh)
colb=np.maximum(colb,D-drim)
np.save('end_colb.npy',colb.astype(np.float32))
wz=np.clip((D-PAR['d_a'])/(PAR['d_b']-PAR['d_a']),0,1); wz=wz*wz*(3-2*wz)
wr=np.clip((R+PAR['zone_r']-RAD)/4.0,0,1); w=wz*wr
print('scan-envelope solid voxels in the collar-only zone outside the ideal collar: %d (%.1f cm3)'%(((fo<0)&(w>0.99)&(colb>0.5)).sum(),((fo<0)&(w>0.99)&(colb>0.5)).sum()*h**3/1000))
fo=fo+w*(colb-fo)
# fill the pocket inside the outer solid. The burn hole leaves gaps, so seal gaps up to ~8 mm wide first:
# a voxel is "outside" only if open air can reach it through a passage wider than that.
from scipy import ndimage as ndi
KS=PAR['seal_vox']; solid=fo<0
dil=ndi.distance_transform_edt(~solid)<=KS
out_lab,_=ndi.label(~dil); edge=np.unique(np.r_[out_lab[0].ravel(),out_lab[-1].ravel(),out_lab[:,0].ravel(),out_lab[:,-1].ravel(),out_lab[:,:,0].ravel(),out_lab[:,:,-1].ravel()]); edge=edge[edge>0]
outside=np.isin(out_lab,edge); del out_lab,dil
reach=ndi.distance_transform_edt(~outside)<=KS+0.5; del outside
void=(~solid)&(~reach); del reach
print('pocket filled: %.1f cm3'%(void.sum()*h**3/1000))
fo[void]=np.minimum(fo[void],-1.0); del void,solid
# remove thin melted flaps standing off the surface and close the cracks beside them (dome zone only)
i66=np.abs(ss-66).argmin(); o66=Lc[i66]; from sweepeval import Tc; t66=Tc[i66]/np.linalg.norm(Tc[i66])
zone=np.zeros(fo.shape,bool)
for i0 in range(0,fo.shape[0],32):
    X=np.stack(np.meshgrid(xs[0][i0:i0+32],xs[1],xs[2],indexing='ij'),-1)
    zone[i0:i0+32]=((X-o66)@t66<0)&(np.linalg.norm(X-c,axis=-1)<85)
zone&=(w<0.5)
solid=fo<0
er=ndi.distance_transform_edt(solid)>PAR['open_r']/h; opened=ndi.distance_transform_edt(~er)<=PAR['open_r']/h; del er
removed=solid&~opened&zone
di=ndi.distance_transform_edt(~opened)<=PAR['close_r']/h; closed=ndi.distance_transform_edt(di)>PAR['close_r']/h; del di
added=closed&~solid&zone&~removed
print('thin flaps removed: %.2f cm3, cracks closed: %.2f cm3'%(removed.sum()*h**3/1000,added.sum()*h**3/1000))
fo[removed]=np.maximum(fo[removed],0.6); fo[added]=np.minimum(fo[added],-0.6)
chg=ndi.binary_dilation(removed|added,iterations=3)
fs_=ndi.gaussian_filter(fo,1.0); fo[chg]=fs_[chg]; del fs_,chg,removed,added,opened,closed,solid,zone
out_lab,_=ndi.label(fo>0); edge=np.unique(np.r_[out_lab[0].ravel(),out_lab[-1].ravel(),out_lab[:,0].ravel(),out_lab[:,-1].ravel(),out_lab[:,:,0].ravel(),out_lab[:,:,-1].ravel()]); edge=edge[edge>0]
void=(fo>0)&~np.isin(out_lab,edge); print('enclosed voids filled at the end: %d voxels'%void.sum()); fo[void]=-0.6; del out_lab,void
np.save('end_fo.npy',fo); np.save('end_D.npy',D); np.save('end_RAD.npy',RAD); np.save('end_w.npy',w.astype(np.float32))
json.dump(PAR|{'box_a':a.tolist(),'box_b':b.tolist(),'A':A.tolist(),'c':c.tolist(),'e1':e1.tolist(),'e2':e2.tolist()},open('end_params.json','w'),indent=1)
print('done',time.time()-t0)
