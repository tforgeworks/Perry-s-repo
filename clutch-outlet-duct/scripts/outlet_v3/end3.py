# Corrected outlet end, step 3: hollow it (2.5 mm wall, collar wall from the scan), open the bore,
# add the rim tab, close it with a flat cut in the tube, and mesh it as a watertight piece.
import numpy as np, json, time, trimesh, fast_simplification, pymeshfix, sys
from skimage import measure
from sweepeval import ss, Lc, Tc
t0=time.time()
p=json.load(open('end_params.json')); a=np.array(p['box_a']); A=np.array(p['A']); c=np.array(p['c']); e1=np.array(p['e1']); e2=np.array(p['e2'])
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
fo=np.load(sys.argv[1] if len(sys.argv)>1 else 'end_fo2.npy'); D=np.load('end_D.npy'); RAD=np.load('end_RAD.npy'); w=np.load('end_w.npy')
R=p['R']; Rin=p['R_in']; t=p['t_wall']; drim=p['d_rim']
# true inward distance from the outer surface (the scan-derived field is not a reliable distance away from scan data)
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
inside=fo<0
din=ndi.distance_transform_edt(inside).astype(np.float32)*h
vs,_,_,_=measure.marching_cubes(fo,0.0); tr=cKDTree(vs)
band=np.argwhere(inside&(din<t+2.5))
for i in range(0,len(band),4_000_000):
    b=band[i:i+4_000_000]; dd,_=tr.query(b.astype(np.float32),workers=4); din[b[:,0],b[:,1],b[:,2]]=dd*h
chan=(1-w)*(t-din)+w*(RAD-Rin)                 # inside surface: exact wall offset in the body, straight bore in the collar
chan=np.where(inside,chan,np.where(w>0.5,RAD-Rin,1.0))
del din,inside
W=np.maximum(fo,-chan)
# ---- rim tab on the far side of the bend (position taken from the sister part; this area is burned away on the scan)
TAB=dict(radial_out_mm=7.0,axial_len_mm=10.0,thick_mm=3.0,below_lip_mm=0.0,edge_round_mm=1.0,fillet_mm=1.0)
i90=np.abs(ss-90).argmin(); tv=(Lc[i90]-c); tv=tv-(tv@A)*A; tv/=np.linalg.norm(tv)       # direction from the collar toward the tube
rdir=-tv; tdir=np.cross(A,rdir)
d1=drim-p['bead_h']-TAB['below_lip_mm']; d0=d1-TAB['axial_len_mm']; r0=R-1.5; r1=R+TAB['radial_out_mm']
ctr=c+A*(d0+d1)/2+rdir*(r0+r1)/2; half=np.array([(d1-d0)/2,(r1-r0)/2,TAB['thick_mm']/2]); Rm=np.stack([A,rdir,tdir])
xs=[(np.arange(a[i],a[i]+W.shape[i])+0.5)*h+lo[i] for i in range(3)]
cor=np.array([ctr+Rm.T@(half*s_) for s_ in np.array(np.meshgrid([-1,1],[-1,1],[-1,1])).reshape(3,-1).T])
ia=np.maximum(np.floor((cor.min(0)-4-lo)/h).astype(int)-a,0); ib=np.minimum(np.ceil((cor.max(0)+4-lo)/h).astype(int)-a,W.shape)
idx=np.indices(ib-ia).reshape(3,-1).T+ia; X=(idx+a+0.5)*h+lo
q=(X-ctr)@Rm.T; rr=TAB['edge_round_mm']; qd=np.abs(q)-(half-rr)
box=np.linalg.norm(np.maximum(qd,0),axis=1)+np.minimum(qd.max(1),0)-rr
box=np.maximum(box,Rin-RAD[idx[:,0],idx[:,1],idx[:,2]])
wv=W[idx[:,0],idx[:,1],idx[:,2]]; k=TAB['fillet_mm']; hh=np.clip(0.5+0.5*(box-wv)/k,0,1)
W[idx[:,0],idx[:,1],idx[:,2]]=np.minimum(wv,box*(1-hh)+wv*hh-k*hh*(1-hh))
# ---- close the piece with a flat cut across the tube at s = 96 and keep away from the array faces
ic=np.abs(ss-96).argmin(); o=Lc[ic]; tb=Tc[ic]/np.linalg.norm(Tc[ic])
for i0 in range(0,W.shape[0],32):
    Xg=np.stack(np.meshgrid(xs[0][i0:i0+32],xs[1],xs[2],indexing='ij'),-1)
    W[i0:i0+32]=np.maximum(W[i0:i0+32],(Xg-o)@tb)
W[[0,-1]]=1; W[:,[0,-1]]=1; W[:,:,[0,-1]]=1
# seal hairline slits and fill enclosed voids in the wall
solid=W<0; st_=ndi.generate_binary_structure(3,1); gaps=ndi.binary_closing(solid,st_,iterations=2)&~solid&(w<0.3)   # not in the collar: it is exact, and closing would roughen the corner under the lip
lab_,n_=ndi.label(~(solid|gaps)); szs=np.bincount(lab_.ravel()); keep_=np.argsort(-szs[1:])[:2]+1   # outside and the air channel are one or two big regions
voids=(~(solid|gaps))&~np.isin(lab_,keep_)
print('slit voxels sealed',int(gaps.sum()),'enclosed void voxels filled',int(voids.sum()))
W[gaps|voids]=np.minimum(W[gaps|voids],-0.15); del lab_,solid,gaps,voids
np.save('end_W.npy',W)
v,f,_,_=measure.marching_cubes(W,0.0,allow_degenerate=False); v=v*h+lo+a*h+h/2
print('mc faces',len(f),time.time()-t0,flush=True)
v2,f2=fast_simplification.simplify(v.astype(np.float32),f.astype(np.int32),target_count=260000)
m=trimesh.Trimesh(v2,f2,process=True)
cc=m.split(only_watertight=False); print('components',sorted(len(x.faces) for x in cc)[-4:])
m=max(cc,key=lambda x:len(x.faces))
mf=pymeshfix.MeshFix(np.asarray(m.vertices,float),np.asarray(m.faces,np.int32)); mf.repair()
m=trimesh.Trimesh(mf.points if hasattr(mf,'points') else mf.v, mf.faces if hasattr(mf,'faces') else mf.f,process=True)
if m.volume<0: m.invert()
print('end piece: faces',len(m.faces),'watertight',m.is_watertight,'bodies',m.body_count,'volume',round(m.volume))
m.export('end_piece.ply')
json.dump(p|{'tab':TAB|{'center':ctr.tolist(),'radial_dir':rdir.tolist()},'toward_tube_dir':tv.tolist()},open('end_params.json','w'),indent=1)
