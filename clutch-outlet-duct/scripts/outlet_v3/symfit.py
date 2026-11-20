# Is the elbow mirror-symmetric about the plane through the collar axis and the tube? Fit the mirror plane on intact overlaps (fast).
import numpy as np, time
from scipy.spatial import cKDTree
from scipy.optimize import least_squares
from sweepeval import ss,Lc,project
t0=time.time()
z=np.load('collar_frame.npz'); A=z['A']; c=z['c']
P=np.load('outerP.npy')[::6].astype(float)
k=np.linalg.norm(P-c,axis=1)<75; Q=P[k]; s,_,_=project(Q); Q=Q[s<72]
rng=np.random.default_rng(0); Qf=Q[rng.choice(len(Q),min(8000,len(Q)),replace=False)]
print('points',len(Q),'fit sample',len(Qf),time.time()-t0,flush=True)
tv=Lc[np.abs(ss-90).argmin()]-c; tv=tv-(tv@A)*A; tv/=np.linalg.norm(tv)
m0=np.cross(A,tv); m0/=np.linalg.norm(m0); tree=cKDTree(Q)
def mirror(p,X):
    m=m0+p[0]*A+p[1]*tv; m/=np.linalg.norm(m); return X-2*((X-c)@m-p[2])[:,None]*m, m
def resid(p): d,_=tree.query(mirror(p,Qf)[0]); return np.minimum(d,3.0)
score=lambda p: np.mean(np.minimum(resid(p),1.5))
r0=resid([0,0,0]); print('start: overlap share (<1.5 mm) %.2f, median of overlaps %.2f'%((r0<1.5).mean(),np.median(r0[r0<1.5])))
best=min(((score([np.tan(np.radians(a1)),np.tan(np.radians(a2)),off]),a1,a2,off) for a1 in np.arange(-12,12.1,3) for a2 in np.arange(-12,12.1,3) for off in (-4,-2,0,2,4)))
print('grid best',best,time.time()-t0,flush=True)
p=least_squares(resid,[np.tan(np.radians(best[1])),np.tan(np.radians(best[2])),best[3]],loss='soft_l1',f_scale=0.4,diff_step=2e-3).x
r=resid(p); _,m=mirror(p,Qf)
print('fitted mirror plane: normal',m.round(3),'tilt from start %.1f deg, offset %.2f mm'%(np.degrees(np.arccos(np.clip(m@m0,-1,1))),p[2]))
print('overlap share (<1.5 mm) %.2f, median %.2f, p90 %.2f mm among overlapping points'%((r<1.5).mean(),np.median(r[r<1.5]),np.percentile(r[r<1.5],90)))
np.savez('mirror_plane.npz',m=m,off=p[2],c=c); print('time',time.time()-t0)
