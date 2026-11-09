import numpy as np
V=np.load('verts.npy'); F=np.load('faces.npy')
fn=np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]])
N=np.zeros_like(V)
for i in range(3): np.add.at(N,F[:,i],fn)
N/=np.linalg.norm(N,axis=1,keepdims=True)+1e-12
np.save('vnorm.npy',N.astype(np.float32))
