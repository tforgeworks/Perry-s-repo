import numpy as np, gc
from scipy import ndimage as ndi
W=np.load('W4.npy',mmap_mode='r'); g=np.load('grid.npy'); lo=g[:3]; h=g[3]
S=np.asarray(W)<0
st=ndi.generate_binary_structure(3,1)
E=ndi.binary_erosion(S,st,iterations=2); O=ndi.binary_dilation(E,st,iterations=2)&S; del E; gc.collect()
T=S&~O; del S
lab,n=ndi.label(T,structure=np.ones((3,3,3))); del T
sz=np.bincount(lab.ravel())[1:]
com=ndi.center_of_mass(lab>0,lab,np.arange(1,n+1)) if n<200000 else None
print('thin components',n)
order=np.argsort(-sz)
np.save('thin_lab.npy',lab.astype(np.int32)); 
for i in order[:25]: print(i+1,sz[i],(np.array(com[i])*h+lo).round(1))
