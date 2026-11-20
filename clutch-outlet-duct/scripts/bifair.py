# Minimum-bending (biharmonic) fill of unscanned outer-surface patches, then rebuild the
# inner wall at a constant offset so the wall keeps its thickness.
import numpy as np, trimesh, json, sys, scipy.sparse as sp, scipy.sparse.linalg as sla
from scipy.spatial import cKDTree
from scipy import ndimage as ndi
src,dst=sys.argv[1],sys.argv[2]; WALL=2.5
m=trimesh.load(src); V=m.vertices.copy(); F=m.faces; n=len(V)
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
E=np.load('sdf_s.npy',mmap_mode='r')
def sampleE(X):
    c=((X-lo)/h-0.5); a=np.floor(c.min(0)).astype(int)-2; b=np.ceil(c.max(0)).astype(int)+3
    a=np.maximum(a,0); b=np.minimum(b,E.shape)
    sub=np.asarray(E[a[0]:b[0],a[1]:b[1],a[2]:b[2]]); return ndi.map_coordinates(sub,(c-a).T,order=1,cval=5)
fr_=np.load('frac_coarse.npy'); gc_=np.load('grid_coarse.npy')
env=lambda X: ndi.map_coordinates(fr_,((X-gc_[:3])/gc_[3]-0.5).T,order=1,cval=0)
Nv=m.vertex_normals
step=env(V+2.5*Nv)
outer=step<0.5
e=np.where(outer,0.0,-2.5)
scan=np.load('outerP.npy')[::2]; ds,_=cKDTree(scan).query(V,workers=4)
p=json.load(open('params.json')); cc=np.array(p['cuff_center']); T=np.array(p['cuff_axis'])
vv=V-cc; d=vv@T; rr=np.linalg.norm(vv-np.outer(d,T),axis=1)
keep=(rr<50)&(d>p['d0']-25)                                   # rebuilt cuff/transition: already designed
cap=cKDTree(np.load('cap_pts.npy')[:300000]); dc,_=cap.query(V,workers=4); keep|=dc<8   # mouth opening
for cen,r in [([-75,-25,24],16),([-148,25,40],34),([-110,-17,57],10)]: keep|=np.linalg.norm(V-cen,axis=1)<r
seed=np.load('circ2_idx.npy')
WHOLE='--whole' in sys.argv
free=outer&~keep if WHOLE else outer&(ds>0.8)&~keep
# restrict to connected patches touching the circled area
A=sp.coo_matrix((np.ones(len(m.edges_unique)*2),(np.r_[m.edges_unique[:,0],m.edges_unique[:,1]],np.r_[m.edges_unique[:,1],m.edges_unique[:,0]])),shape=(n,n)).tocsr()
sub=A[free][:,free]; nc,lab=sp.csgraph.connected_components(sub,directed=False)
fidx=np.where(free)[0]; sl=set(lab[np.isin(fidx,seed)])
free_v=fidx[np.isin(lab,list(sl))]
if WHOLE:
    dseed,_=cKDTree(V[seed]).query(V,workers=4)
    free_v=np.where(outer&~keep&(dseed<4.0))[0]
    print('solid patch verts',len(free_v))
# grow by 3 rings so the fill blends into the scanned surface (slope-continuous)
fm=np.zeros(n,bool); fm[free_v]=True
GROW=int([a for a in sys.argv if a.startswith('--grow=')][0][7:]) if any(a.startswith('--grow=') for a in sys.argv) else 3
for i in range(GROW): fm|=(A@fm.astype(float)>0)&outer&~keep
free_v=np.where(fm)[0]
print('outer vertices refilled',len(free_v),'patches',len(sl))
# cotangent Laplacian + lumped mass
def cot(a,b): 
    return np.einsum('ij,ij->i',a,b)/np.maximum(np.linalg.norm(np.cross(a,b),axis=1),1e-12)
I=[];J=[];W=[]
for k in range(3):
    i,j,o=F[:,k],F[:,(k+1)%3],F[:,(k+2)%3]
    w=0.5*cot(V[i]-V[o],V[j]-V[o]); w=np.clip(w,0,None)
    I+= [i,j]; J+=[j,i]; W+=[w,w]
I=np.concatenate(I);J=np.concatenate(J);W=np.concatenate(W)
Wm=sp.coo_matrix((W,(I,J)),shape=(n,n)).tocsr()
L=sp.diags(np.asarray(Wm.sum(1)).ravel())-Wm
ar=np.linalg.norm(np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]]),axis=1)/6
M=np.bincount(F.ravel(),np.repeat(ar,3),n); Mi=sp.diags(1/np.maximum(M,1e-9))
Q=(L@Mi@L).tocsr()
fr=free_v; fx=np.setdiff1d(np.arange(n),fr)
ELL=float([a for a in sys.argv if a.startswith('--ell=')][0][6:]) if any(a.startswith('--ell=') for a in sys.argv) else 0
lam=(1/ELL**4) if ELL>0 else 0.0
Md=sp.diags(M)
Qff=(Q+lam*Md)[fr][:,fr]; Qfx=Q[fr][:,fx]
Vn=V.copy()
solve=sla.factorized(Qff.tocsc()); del Qff
for c in range(3): Vn[fr,c]=solve(-(Qfx@V[fx,c])+lam*M[fr]*V[fr,c])
mv=np.linalg.norm(Vn-V,axis=1)[fr]; del solve,Qfx; import gc; gc.collect()
print('outer fill moved: median %.2f p95 %.2f max %.2f mm'%(np.median(mv),np.percentile(mv,95),mv.max()))
m2=m.copy(); m2.vertices=Vn
# inner wall: its own minimum-bending fill over the matching patch (boundary fixed to the existing wall)
inner=(e<-1.0)&~keep
near=cKDTree(Vn[fr]); di,_=near.query(V,workers=4)
fi=inner&(di<WALL+4.0)
fi_idx=np.where(fi)[0]
for i in range(2): fi|=(A@fi.astype(float)>0)&inner
fi_idx=np.where(fi)[0]; fx2=np.setdiff1d(np.arange(n),fi_idx)
solve2=sla.factorized(Q[fi_idx][:,fi_idx].tocsc())
Qfx2=Q[fi_idx][:,fx2]
for c in range(3): Vn[fi_idx,c]=solve2(-(Qfx2@Vn[fx2,c]))
print('inner vertices refilled',len(fi_idx))
np.save('bifair_inner.npy',fi_idx)
m2.vertices=Vn; m2.export(dst)
np.save('bifair_free.npy',fr)
print('watertight',m2.is_watertight)
