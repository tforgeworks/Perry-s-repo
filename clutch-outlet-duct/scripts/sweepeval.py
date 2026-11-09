import numpy as np, json
from scipy.interpolate import BSpline
from scipy.spatial import cKDTree
F=np.load('sweep_frame.npz'); ss,Lc,Tc,E1,E2=F['ss'],F['Lc'],F['Tc'],F['E1'],F['E2']
C=np.load('sweep_coef.npz'); c,tk,K,lo_s,hi_s=C['c'],C['tk'],int(C['K']),float(C['lo_s']),float(C['hi_s'])
_tree=cKDTree(Lc)
def project(X):
    _,i=_tree.query(X,workers=4)
    v=X-Lc[i]; a=np.einsum('ij,ij->i',v,Tc[i]); s=ss[i]+a
    v=v-a[:,None]*Tc[i]; rho=np.linalg.norm(v,axis=1); th=np.arctan2(np.einsum('ij,ij->i',v,E2[i]),np.einsum('ij,ij->i',v,E1[i]))
    return s,th,rho
def radius(s,th):
    s=np.clip(s,lo_s,hi_s-1e-6)
    Bs=BSpline.design_matrix(s,tk,3)
    ph=[np.ones_like(th)]+[f(k*th) for k in range(1,K+1) for f in (np.cos,np.sin)]
    Ph=np.stack(ph,1); nb=len(tk)-4
    Cm=c.reshape(nb,2*K+1)
    return np.einsum('ij,ij->i',(Bs@Cm),Ph)
def surface_mesh(s0,s1,ns=400,nt=360):
    S=np.linspace(s0,s1,ns); TH=np.linspace(-np.pi,np.pi,nt,endpoint=False)
    SS,TT=np.meshgrid(S,TH,indexing='ij'); r=radius(SS.ravel(),TT.ravel()).reshape(SS.shape)
    i=np.clip(np.searchsorted(ss,S),0,len(ss)-1)
    P=Lc[i][:,None,:]+r[...,None]*(np.cos(TT)[...,None]*E1[i][:,None,:]+np.sin(TT)[...,None]*E2[i][:,None,:])
    V=P.reshape(-1,3); f=[]
    for a in range(ns-1):
        for b in range(nt):
            p0=a*nt+b; p1=a*nt+(b+1)%nt; p2=(a+1)*nt+b; p3=(a+1)*nt+(b+1)%nt
            f+= [[p0,p2,p1],[p1,p2,p3]]
    return V,np.array(f)
