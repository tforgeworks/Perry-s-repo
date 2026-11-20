import numpy as np
from scipy import ndimage as ndi
P=np.load('P.npy').astype(np.float32); N=np.load('PN.npy').astype(np.float32)
fr=np.load('frac_coarse.npy'); g=np.load('grid_coarse.npy'); lo=g[:3];H=g[3]
def samp(X):
    c=((X-lo)/H-0.5).T
    return ndi.map_coordinates(fr,c,order=1,mode='constant',cval=0)
d=1.5
fo=samp(P+d*N); fi=samp(P-d*N)
keep=(fo<0.5)&(fi>0.5)
flip=(fo>0.5)&(fi<0.5)
print('n',len(P),'keep',keep.sum(),'flipped',flip.sum(),'drop',(~keep&~flip).sum())
Pk=np.r_[P[keep],P[flip]]; Nk=np.r_[N[keep],-N[flip]]
np.save('outerP.npy',Pk); np.save('outerN.npy',Nk)
