import numpy as np, trimesh, scipy.sparse as sp, json
from scipy.spatial import cKDTree
from scipy import ndimage as ndi
WALL=2.5
m0=trimesh.load('sweep_mls3.ply',process=False); mf=trimesh.load('bifair.ply',process=False)
F=m0.faces; V0=m0.vertices; n=len(V0)
fo=np.load('bifair_free.npy')
V=V0.copy(); V[fo]=mf.vertices[fo]                     # faired outer patch, original inner wall
g=np.load('grid.npy'); lo=g[:3]; h=g[3]; E=np.load('sdf_s.npy',mmap_mode='r')
def sampleE(X):
    c=((X-lo)/h-0.5); a=np.maximum(np.floor(c.min(0)).astype(int)-2,0); b=np.minimum(np.ceil(c.max(0)).astype(int)+3,E.shape)
    return ndi.map_coordinates(np.asarray(E[a[0]:b[0],a[1]:b[1],a[2]:b[2]]),(c-a).T,order=1,cval=5)
fr_=np.load('frac_coarse.npy'); gc_=np.load('grid_coarse.npy')
env=lambda X: ndi.map_coordinates(fr_,((X-gc_[:3])/gc_[3]-0.5).T,order=1,cval=0)
step=env(V0+2.5*m0.vertex_normals); outer=step<0.5; inner=~outer
A=sp.coo_matrix((np.ones(len(m0.edges_unique)*2),(np.r_[m0.edges_unique[:,0],m0.edges_unique[:,1]],np.r_[m0.edges_unique[:,1],m0.edges_unique[:,0]])),shape=(n,n)).tocsr()
Mavg=sp.diags(1/np.asarray(A.sum(1)).ravel())@A
# outer reference patch = refilled verts + 6 rings of outer neighbours
pm=np.zeros(n,bool); pm[fo]=True
for i in range(6): pm|=(A@pm.astype(float)>0)&outer
pf=np.where(pm[F].all(1))[0]
ref=trimesh.Trimesh(V,F[pf],process=False)
ci=np.where(inner&(cKDTree(V[fo]).query(V0,workers=4)[0]<WALL+3.0))[0]
print('inner verts considered',len(ci))
pq=trimesh.proximity.ProximityQuery(ref)
for it in range(4):
    q,dist,tri=pq.on_surface(V[ci]); nq=ref.face_normals[tri]
    d=np.einsum('ij,ij->i',q-V[ci],nq)
    disp=np.zeros((n,3)); w=np.zeros(n)
    ok=(d>0.3)&(d<WALL+3.0)
    disp[ci[ok]]=((d[ok]-WALL))[:,None]*nq[ok]; w[ci[ok]]=1
    # blend toward boundary of the refilled patch (distance from patch interior)
    for k in range(8): disp=0.5*disp+0.5*(Mavg@disp); w=0.5*w+0.5*(Mavg@w)
    disp=np.where(w[:,None]>1e-6,disp/np.maximum(w,1e-6)[:,None]*np.clip(w*2,0,1)[:,None],0)
    disp[~inner]=0
    V+=disp
    print(it,'wall before step: median %.2f p5 %.2f p95 %.2f'%(np.median(d[ok]),np.percentile(d[ok],5),np.percentile(d[ok],95)))
q,dist,tri=pq.on_surface(V[ci]); d=np.einsum('ij,ij->i',q-V[ci],ref.face_normals[tri]); ok=(d>0)&(d<WALL+3)
print('final wall on patch: min %.2f p5 %.2f median %.2f p95 %.2f'%(d[ok].min(),np.percentile(d[ok],5),np.median(d[ok]),np.percentile(d[ok],95)))
m=trimesh.Trimesh(V,F,process=False); m.export('bifair2.ply'); print('watertight',m.is_watertight)
