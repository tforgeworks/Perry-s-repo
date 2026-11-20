# Superimposition check: original scan vs revised v3 model, both in scan coordinates (no re-alignment applied).
import numpy as np, trimesh, json, time
from scipy.spatial import cKDTree
from sweepeval import project
t0=time.time()
p=json.load(open('end_params.json')); A=np.array(p['A']); c=np.array(p['c'])
m=trimesh.load('v3_pca_fixed.ply')
S,fi=m.sample(9_000_000,return_index=True); SN=m.face_normals[fi]; tree=cKDTree(S)
P=np.load('P.npy')[::3].astype(float)
dd,ii=tree.query(P,workers=-1)
pl=np.einsum('ij,ij->i',P-S[ii],SN[ii])                 # signed distance to the model surface along its outward normal
dist=np.where((dd<1.0)&(np.abs(pl)<=dd+0.05),np.abs(pl),dd); sd=np.sign(pl)*dist; sd[pl==0]=0
print('distances',time.time()-t0,flush=True)
s,_,rho=project(P); X=P-c; dc=np.linalg.norm(X,axis=1); d_ax=X@A
end=(dc<95)&(s<66)
region=np.where(end&(d_ax>=3),3,np.where(end,2,np.where((s>=66)&(s<262)&(rho<75),1,0)))
names=['Box, mouth and mounting ear','Tube','Elbow at the outlet end','Outlet cuff']
out={'note':'Scan points to the nearest model surface. Both are in the scan\'s own coordinates; no re-alignment was applied. Positive = scan stands proud of the model.','scan_points_used':int(len(P))}
def st(x,sx): return dict(scan_points=int(len(x)),median_mm=round(float(np.median(x)),3),p95_mm=round(float(np.percentile(x,95)),3),within_0_25mm=round(float((x<0.25).mean()),4),within_0_5mm=round(float((x<0.5).mean()),4),within_1mm=round(float((x<1).mean()),4),mean_signed_mm=round(float(np.mean(sx)),3))
out['all']=st(dist,sd)
for k,nm in enumerate(names): out[nm]=st(dist[region==k],sd[region==k]); print(nm,out[nm])
print('all',out['all'])
# is any shift or rotation needed? best-fit rigid correction on the trusted regions (point-to-plane, one linear step)
k=(region<=1)&(dist<1.0); q=P[k][::5]; n=SN[ii[k]][::5]; r=pl[k][::5]
Jm=np.c_[np.cross(q-q.mean(0),n),n]; x,*_=np.linalg.lstsq(Jm,-r,rcond=None)
ang=np.degrees(np.linalg.norm(x[:3])); tr=np.linalg.norm(x[3:]); r2=r+Jm@x
out['best_fit_correction_on_box_and_tube']=dict(rotation_deg=round(float(ang),4),translation_mm=round(float(tr),4),largest_point_shift_mm=round(float(np.abs(Jm@x).max()),3),rms_before_mm=round(float(np.sqrt((r**2).mean())),4),rms_after_mm=round(float(np.sqrt((r2**2).mean())),4))
print(out['best_fit_correction_on_box_and_tube'])
# model surface not backed by scan data
PN=np.load('PN.npy')[::3]
ts=cKDTree(P); Sm=S[::3]; dm,_=ts.query(Sm,workers=-1)
out['model_surface_with_scan_within_1mm']=round(float((dm<1.0).mean()),4)
json.dump(out,open('superimpose.json','w'),indent=1)
np.savez('superimpose.npz',P=P.astype(np.float32),PN=PN,sd=sd.astype(np.float32),region=region.astype(np.int8),S=Sm.astype(np.float32),SN=SN[::3].astype(np.float32),dm=dm.astype(np.float32))
print('done',time.time()-t0)
