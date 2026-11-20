# Collar fit from its own walls: band above the crease with the tube and below the lip, both faces, robust.
import numpy as np
from scipy.optimize import least_squares
P=np.load('P.npy').astype(float); N=np.load('PN.npy').astype(float)
z=np.load('cuff3_inner.npz'); a0=z['axis']/np.linalg.norm(z['axis']); c0=z['center']
k=np.linalg.norm(P-c0,axis=1)<60; Q=P[k][::2]; M=N[k][::2]
def frame(a):
    a=a/np.linalg.norm(a); e1=np.cross(a,[0,0,1.]); e1/=np.linalg.norm(e1); return a,e1,np.cross(a,e1)
A0,E1,E2=frame(a0)
def geom(p,Q):
    a=A0+p[0]*E1+p[1]*E2; a/=np.linalg.norm(a); c=c0+p[2]*E1+p[3]*E2
    v=Q-c; d=v@a; rv=v-np.outer(d,a); rad=np.linalg.norm(rv,axis=1); return a,c,d,rv/rad[:,None],rad
res={}
for band in [(2,16),(0,18),(4,14),(-4,16)]:
    p=np.array([0,0,0,0,30.3,26.9])
    for it in range(12):
        a,c,d,rh,rad=geom(p,Q); radial=np.einsum('ij,ij->i',M,rh); tol=3.0 if it<3 else 1.2 if it<7 else 0.7
        base=(d>band[0])&(d<band[1])&(np.abs(M@a)<0.3)
        so=base&(radial>0.8)&(np.abs(rad-p[4])<tol); si=base&(radial<-0.8)&(np.abs(rad-p[5])<tol)
        p=least_squares(lambda q: np.r_[geom(q,Q[so])[4]-q[4],geom(q,Q[si])[4]-q[5]],p,loss='soft_l1',f_scale=0.25).x
    a,c,d,rh,rad=geom(p,Q); _,e1,e2=frame(a); th=np.degrees(np.arctan2(rh@e2,rh@e1))
    covo=len(np.unique(th[so]//10))*10; covi=len(np.unique(th[si]//10))*10
    print('band d %s: axis %s  center %s  R_out %.2f (D %.1f)  R_in %.2f  wall %.2f  n %d/%d  rms %.2f/%.2f  coverage %d/%d deg'%(band,a.round(3),c.round(1),p[4],2*p[4],p[5],p[4]-p[5],so.sum(),si.sum(),np.sqrt(((rad[so]-p[4])**2).mean()),np.sqrt(((rad[si]-p[5])**2).mean()),covo,covi))
    res[band]=(a,c,p[4],p[5])
a,c,Ro,Ri=res[(2,16)]; np.savez('cuff4.npz',axis=a,center=c,R=Ro,R_in=Ri)
old=np.array([-0.504,0.826,-0.252]); print('angle between this axis and the one I used for the first v3 build: %.1f deg'%np.degrees(np.arccos(a@old/np.linalg.norm(old))))
