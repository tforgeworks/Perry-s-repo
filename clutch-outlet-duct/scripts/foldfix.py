import numpy as np, trimesh, scipy.sparse as sp, sys
m0=trimesh.load(sys.argv[1]); m=trimesh.load(sys.argv[2])
def folds(m):
    ang=m.face_adjacency_angles; bad=m.face_adjacency[ang>np.radians(35)]
    return np.unique(m.faces[bad.ravel()].ravel())
b0=folds(m0); new=np.setdiff1d(folds(m),b0)
V=m.vertices.copy(); n=len(V)
e=m.edges_unique; A=sp.coo_matrix((np.ones(2*len(e)),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(n,n)).tocsr()
Mavg=sp.diags(1/np.asarray(A.sum(1)).ravel())@A
w=np.zeros(n); w[new]=1
for i in range(6): w=np.maximum(w,Mavg@w)
w=np.clip(w*1.5,0,1)
s=m.copy(); trimesh.smoothing.filter_taubin(s,lamb=0.5,nu=-0.53,iterations=40)
m.vertices=V+w[:,None]*(s.vertices-V)
print('new folds before fix',len(new),'after',len(np.setdiff1d(folds(m),b0)),'watertight',m.is_watertight)
m.export(sys.argv[3])
