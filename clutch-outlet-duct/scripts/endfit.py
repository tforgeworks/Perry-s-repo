import numpy as np
from scipy.optimize import least_squares
P=np.load('outerP.npy').astype(float)
c0,T,e1,e2=np.load('endframe.npy')
d=(P-c0)@T; q=np.c_[(P-c0)@e1,(P-c0)@e2]
for lo_,hi_ in [(-15,-5),(-10,0),(-5,5),(0,10),(5,15),(10,20),(-10,15)]:
    k=(d>lo_)&(d<hi_)&(np.hypot(q[:,0],q[:,1])<45)&(q[:,1]<22)&(q[:,0]>-25)  # exclude crushed top & torn left flap
    x=q[k]
    r=least_squares(lambda p: np.hypot(x[:,0]-p[0],x[:,1]-p[1])-p[2],[0,0,34],loss='soft_l1',f_scale=0.3)
    print((lo_,hi_),'n',k.sum(),'center',r.x[:2].round(2),'R',r.x[2].round(2),'D',(2*r.x[2]).round(2),'med res',np.median(np.abs(r.fun)).round(2))
