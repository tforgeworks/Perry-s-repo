import numpy as np, time, gc, json
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
t0=time.time()
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
PAR=json.load(open('params_in.json'))
c0,T,e1,e2=np.load('endframe.npy')
cc=c0+PAR['cuff_center_offset_e1']*e1+PAR['cuff_center_offset_e2']*e2
Ro=PAR['Ro']; t=PAR['t_wall']; tc=PAR['t_cuff']; dend=PAR['d_end']; d0=PAR['d0']; d1=PAR['d1']
PADX=90
Fa=np.pad(np.load('Fa.npy'),((0,PADX),(0,0),(0,0)),constant_values=5.0); shape=Fa.shape
wz=np.pad(np.load('wzone.npy'),((0,PADX),(0,0),(0,0)),constant_values=0.0)
DA=np.pad(np.load('dall.npy'),((0,PADX),(0,0),(0,0)),constant_values=10.0)
print('fill smooth',time.time()-t0,flush=True)
E=np.pad(np.load('sdf_s.npy'),((0,PADX),(0,0),(0,0)),constant_values=5.0)
UPA=np.load('upsec.npy'); UP=UPA[:2]; RUP=UPA[2:]
_,_,e1,e2=np.load('upframe.npy')
Eh=ndi.gaussian_filter(E,PAR['flap_sigma']/h).astype(np.float16)
Em=ndi.gaussian_filter(E,PAR['melt_sigma']/h).astype(np.float16)
Es=ndi.gaussian_filter(E,PAR['fill_sigma']/h).astype(np.float16)
xs=[(np.arange(n)+0.5)*h+lo[i] for i,n in enumerate(shape)]
W=np.empty(shape,np.float32)
dA=d0-PAR['handover']
for i0 in range(0,shape[0],16):
    i1=min(shape[0],i0+16)
    X=np.stack(np.meshgrid(xs[0][i0:i1],xs[1],xs[2],indexing='ij'),-1).astype(np.float32)
    f=Fa[i0:i1]; fe=E[i0:i1]
    r0=np.linalg.norm(X-c0,axis=-1)
    wm=np.clip(1-(r0-PAR['melt_r_full'])/PAR['melt_r_fade'],0,1)
    zz=wz[i0:i1]
    Ez=np.where(wm>0,Em[i0:i1],Es[i0:i1]); wzz=np.maximum(wm,zz)
    Ws=np.maximum(np.maximum(f,-f-t),DA[i0:i1].astype(np.float32)-(t+PAR['support_slack']))
    Wz=np.maximum(Ez,-Ez-t)
    Ws=Ws+wzz*(Wz-Ws)
    V=X-cc; d=V@T; rad=np.linalg.norm(V-d[...,None]*T,axis=-1)
    local=rad<PAR['local_R']
    Fc=np.maximum(rad-Ro,d-dend)
    w=np.clip((d-d0)/(d1-d0),0,1); w=w*w*(3-2*w)
    uu=V@e1; vv=V@e2
    cxu=(1-w)*UP[0]; cxv=(1-w)*UP[1]
    th=np.arctan2(vv-cxv,uu-cxu); rho=np.hypot(uu-cxu,vv-cxv)
    bi=((th+np.pi)/(2*np.pi)*360).astype(int)%360
    fL=rho-((1-w)*RUP[bi]+w*Ro)
    fo=np.where(d<d0,fe,np.where(d>d1,Fc,fL))
    fo=np.where(d>dend,np.maximum(fo,d-dend),fo)
    tt=t+(tc-t)*w
    We=np.maximum(fo,-fo-tt)
    # open bore through the cuff end
    We=np.where(d>d1,np.maximum(We,(Ro-tc)-rad),We)
    # handover from scan-wall field to envelope-based wall field between dA-5 and dA
    u=np.clip((d-(dA-5))/5,0,1); u=np.where(local,u,0)
    Wf=np.where(u>0,(1-u)*Ws+u*We,Ws)
    wc=np.clip(1-(r0-PAR['flap_r_full'])/20.0,0,1)
    W[i0:i1]=np.where(wc>0,np.maximum(Wf,wc*np.where(d<d0,Eh[i0:i1]-PAR['flap_slack'],-1e3)+(1-wc)*(-1e3)),Wf)
del Fa,Eh,Em,Es; gc.collect()
W=ndi.gaussian_filter(W,PAR['final_sigma']/h)
np.save('W3.npy',W)
json.dump(PAR|{'cuff_center':cc.tolist(),'cuff_axis':T.tolist()},open('params.json','w'),indent=1)
print('done',time.time()-t0)
