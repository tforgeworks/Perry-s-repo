# Orient fill-patch normals outward using the solid outer-surface field.
import numpy as np
from scipy import ndimage as ndi
F=np.load('sdf_s.npy',mmap_mode='r'); g=np.load('grid.npy'); lo=g[:3];h=g[3]
A=np.load('fill_pts.npy'); P=A[:,:3];N=A[:,3:]
idx=np.floor((P-lo)/h).astype(int); a=idx.min(0)-8; b=idx.max(0)+8
sub=np.asarray(F[a[0]:b[0],a[1]:b[1],a[2]:b[2]])
s=lambda X: ndi.map_coordinates(sub,((X-lo)/h-0.5-a).T,order=1)
flip=s(P+N)<s(P-N); N[flip]*=-1; np.save('fill_pts.npy',np.c_[P,N].astype(np.float32))
