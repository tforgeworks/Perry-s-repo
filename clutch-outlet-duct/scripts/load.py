import numpy as np, sys, time
p=sys.argv[1]
n=np.fromfile(p,dtype='<u4',count=1,offset=80)[0]
dt=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')])
t=time.time()
d=np.memmap(p,dtype=dt,mode='r',offset=84,shape=(n,))
V=np.array(d['v'])
print('tris',n, 'load s',time.time()-t)
P=V.reshape(-1,3)
print('min',P.min(0),'max',P.max(0),'ext',P.max(0)-P.min(0))
# unique verts
t=time.time()
u,inv=np.unique(P,axis=0,return_inverse=True)
print('unique verts',len(u),time.time()-t)
F=inv.reshape(-1,3).astype(np.int32)
np.save('verts.npy',u.astype(np.float64)); np.save('faces.npy',F)
