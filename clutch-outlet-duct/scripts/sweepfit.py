# Design-intent fit of the tube: smooth centerline + smooth cross-sections (Fourier in angle,
# cubic B-spline along length), fitted robustly to the outer scan points so that surface crust
# (outward) and heat dents / shrink spots (inward) are treated as outliers.
import numpy as np, json
from scipy.interpolate import splprep, splev, BSpline
from scipy.spatial import cKDTree
S0,S1=float(json.load(open('sweep_in.json'))['s0']),float(json.load(open('sweep_in.json'))['s1'])
CFG=json.load(open('sweep_in.json'))
CL=np.load('centerline.npy'); L=CL[:,:3]; arc=CL[:,6]
# fair centerline: smoothing spline through the skeleton centerline
tck,u=splprep(L.T,u=arc,s=len(L)*CFG['cl_smooth'],k=5)
ss=np.linspace(0,arc[-1],6000); Lc=np.array(splev(ss,tck)).T; Tc=np.array(splev(ss,tck,der=1)).T; Tc/=np.linalg.norm(Tc,axis=1,keepdims=True)
# rotation-minimizing frame
E1=np.zeros_like(Tc); e=np.cross(Tc[0],[0,0,1.]); e/=np.linalg.norm(e); E1[0]=e
for i in range(1,len(ss)):
    e=E1[i-1]-(E1[i-1]@Tc[i])*Tc[i]; E1[i]=e/np.linalg.norm(e)
E2=np.cross(Tc,E1)
np.savez('sweep_frame.npz',ss=ss,Lc=Lc,Tc=Tc,E1=E1,E2=E2)
def project(X):
    t=cKDTree(Lc); _,i=t.query(X,workers=4)
    v=X-Lc[i]; a=np.einsum('ij,ij->i',v,Tc[i]); s=ss[i]+a   # small along-tangent correction
    v=v-a[:,None]*Tc[i]; rho=np.linalg.norm(v,axis=1); th=np.arctan2(np.einsum('ij,ij->i',v,E2[i]),np.einsum('ij,ij->i',v,E1[i]))
    return s,th,rho
K=CFG['harmonics']; knot=CFG['knot_mm']
lo_s,hi_s=S0-CFG['margin'],S1+CFG['margin']
nint=int(np.ceil((hi_s-lo_s)/knot)); t_in=np.linspace(lo_s,hi_s,nint+1)
tk=np.r_[[lo_s]*3,t_in,[hi_s]*3]; nb=len(tk)-4
def basis(s,th):
    s=np.clip(s,lo_s,hi_s-1e-6)
    Bs=BSpline.design_matrix(s,tk,3).toarray().astype(np.float32)
    ph=[np.ones_like(th)]+[f(k*th) for k in range(1,K+1) for f in (np.cos,np.sin)]
    Ph=np.stack(ph,1).astype(np.float32)
    return (Bs[:,:,None]*Ph[:,None,:]).reshape(len(s),-1)
if __name__=='__main__':
    P=np.load('outerP.npy').astype(np.float64)
    s,th,rho=project(P)
    sel=(s>max(lo_s,CFG.get('fit_s_min',lo_s)))&(s<hi_s)&(rho<70)
    rng=np.random.default_rng(0); idx=np.where(sel)[0]; idx=rng.choice(idx,min(len(idx),700000),replace=False)
    s,th,rho=s[idx],th[idx],rho[idx]
    X=basis(s,th); nc=X.shape[1]
    # smoothness penalty along s (second differences of spline coeffs, per harmonic)
    D=np.diff(np.eye(nb),2,axis=0); R=np.kron(D.T@D,np.eye(2*K+1))*CFG['lambda']
    w=np.ones(len(s),np.float32); c=None
    for it in range(10):
        Xw=X*w[:,None]; A=Xw.T@X+R; b=Xw.T@rho
        c=np.linalg.solve(A,b); r=rho-X@c
        # asymmetric robust weights: outward crust and inward dents both down-weighted
        so=CFG['scale_out']; si=CFG['scale_in']
        w=np.where(r>0,1/(1+(r/so)**2),1/(1+(r/si)**2)).astype(np.float32)
        print(it,'residual median %.3f  p5 %.3f p95 %.3f  outliers out>0.4: %.1f%%  in<-0.6: %.1f%%'%(np.median(r),np.percentile(r,5),np.percentile(r,95),100*(r>0.4).mean(),100*(r<-0.6).mean()),flush=True)
    np.savez('sweep_coef.npz',c=c,tk=tk,K=K,lo_s=lo_s,hi_s=hi_s)
    # residual by s band
    for a in range(int(lo_s),int(hi_s),20):
        k=(s>=a)&(s<a+20); 
        if k.any(): print('s %3d-%3d  median r %+.3f  crust>0.4 %.1f%%  dent<-0.6 %.1f%%'%(a,a+20,np.median(r[k]),100*(r[k]>0.4).mean(),100*(r[k]<-0.6).mean()))
