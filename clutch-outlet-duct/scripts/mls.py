# Smart smoothing for the box: robust bilateral moving-least-squares.
# Each vertex is moved onto a quadratic patch fitted to nearby vertices on the same face
# (normals within ~30 deg), with outlier rejection, so seams, bumps and dents go away
# while edges, fillets and overall size stay.  Protected features are left untouched.
import numpy as np, trimesh, json, sys
from scipy.spatial import cKDTree
src,dst=sys.argv[1],sys.argv[2]
RAD=float(sys.argv[3]) if len(sys.argv)>3 else 7.0
m=trimesh.load(src)
if src.endswith('.stl'):
    A_=np.load('pca_T.npy'); m.vertices=(m.vertices-A_[0])@A_[1:].T
V=m.vertices.copy(); N=m.vertex_normals.copy()
PASSES=int(sys.argv[5]) if len(sys.argv)>5 else 2; CLAMP=float(sys.argv[6]) if len(sys.argv)>6 else 1.5
p=json.load(open('params.json')); cc=np.array(p['cuff_center']); T=np.array(p['cuff_axis'])
w=np.ones(len(V))
def protect(center,r_full,r_fade):
    d=np.linalg.norm(V-np.asarray(center),axis=1); return np.clip((d-r_full)/r_fade,0,1)
w*=protect([-75,-25,24],14,8); w*=protect([-148,25,40],32,10); w*=protect([-110,-17,57],9,6)
cap=cKDTree(np.load('cap_pts.npy')[:300000]); dc,_=cap.query(V,workers=4); w*=np.clip((dc-6)/6,0,1)
v=V-cc; d=v@T; rr=np.linalg.norm(v-np.outer(d,T),axis=1); w*=np.where((rr<50)&(d>p['d0']-10),0,1)
if len(sys.argv)>4 and sys.argv[4].endswith('.npy'):
    dz,_=cKDTree(np.load(sys.argv[4])).query(V,workers=4); region=np.clip(1-(dz-4)/12,0,1)
else:
    region=(V[:,0]<float(sys.argv[4])) if len(sys.argv)>4 else np.ones(len(V),bool)
w*=region
idx=np.where(w>0)[0]; print('vertices treated',len(idx),flush=True)
V_start=V.copy()
for ps in range(PASSES):
    tree=cKDTree(V)
    # smoothed normals: average over 3 mm so crease/groove vertices are judged by their surroundings
    nbn=tree.query_ball_point(V[idx],3.0,workers=4)
    Ns=N.copy()
    for a_,i in enumerate(idx):
        J=np.array(nbn[a_]); n=N[J][N[J]@N[i]>-0.2].sum(0); Ns[i]=n/(np.linalg.norm(n)+1e-12)
    out=V.copy()
    SUB=max(1,int((RAD/8)**2)); sub=np.arange(0,len(V),SUB); tsub=cKDTree(V[sub])
    for start in range(0,len(idx),1500):
        ii=idx[start:start+1500]
        nb=[sub[np.array(j,int)] for j in tsub.query_ball_point(V[ii],RAD,workers=4)]
        for a_,i in enumerate(ii):
            J=np.array(nb[a_]); n0=Ns[i]
            J=J[Ns[J]@n0>0.85]
            if len(J)<12: continue
            e1=np.cross(n0,[1,0,0])
            if np.linalg.norm(e1)<0.1: e1=np.cross(n0,[0,1,0])
            e1/=np.linalg.norm(e1); e2=np.cross(n0,e1)
            q=V[J]-V[i]; x=q@e1; y=q@e2; z=q@n0
            A=np.stack([np.ones_like(x),x,y,x*x,x*y,y*y],1)
            ws=np.exp(-(x*x+y*y)/(2*(RAD/2)**2)); wt=ws.copy()
            for it in range(4):
                sw=np.sqrt(wt); coef,*_=np.linalg.lstsq(A*sw[:,None],z*sw,rcond=None)
                r=z-A@coef; sc=max(1.4826*np.median(np.abs(r)),0.05)
                u=r/(4.0*sc); wt=ws*np.where(np.abs(u)<1,(1-u*u)**2,0)
            out[i]=V[i]+w[i]*np.clip(coef[0],-CLAMP,CLAMP)*n0
    V=out; m.vertices=V; N=m.vertex_normals.copy()
    print('pass',ps,'done',flush=True)
out=V; V=V_start
m.vertices=out; m.export(dst)
mv=np.linalg.norm(out-V,axis=1); print(dst,'moved median %.3f p99 %.3f max %.3f'%(np.median(mv[idx]),np.percentile(mv[idx],99),mv.max()))
