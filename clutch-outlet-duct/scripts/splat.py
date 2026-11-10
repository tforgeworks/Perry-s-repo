import numpy as np, time
h=0.35
P=np.load('P.npy').astype(np.float64)
# drop tiny floating components: use main component vertex set approx by distance? keep all for now
lo=P.min(0)-6; hi=P.max(0)+6
shape=np.ceil((hi-lo)/h).astype(int)+1
print('shape',shape,np.prod(shape)/1e6,'M')
idx=np.floor((P-lo)/h).astype(np.int32)
S=np.zeros(shape,bool); S[idx[:,0],idx[:,1],idx[:,2]]=True
np.save('surf.npy',S); np.save('grid.npy',np.r_[lo,[h]])
print('surf vox',S.sum())
