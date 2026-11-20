import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
P=np.load('P.npy').astype(float)
ms=np.load('minsec.npy')
T=-ms[3:8,4:7].mean(0); T/=np.linalg.norm(T)   # flow direction toward outlet end
c0=ms[7,1:4]  # arc 25 center
e1=np.cross(T,[0,0,1.]);e1/=np.linalg.norm(e1);e2=np.cross(T,e1)
print('T',T.round(3),'c0',c0.round(1))
d=(P-c0)@T; q1=(P-c0)@e1; q2=(P-c0)@e2
near=np.hypot(q1,q2)<60
fig,ax=plt.subplots(2,5,figsize=(25,10))
for A,l in zip(ax.flat,[-30,-20,-10,-5,0,5,10,15,20,25]):
    k=near&(np.abs(d-l)<0.2)
    A.plot(q1[k],q2[k],',k'); A.set_aspect('equal'); A.set_title(f'd={l}'); A.grid(alpha=.3); A.set_xlim(-50,50); A.set_ylim(-50,50)
    A.add_patch(plt.Circle((0,0),35,fill=False,color='r',lw=0.5)); A.add_patch(plt.Circle((0,0),32.5,fill=False,color='b',lw=0.5))
plt.tight_layout(); plt.savefig('endrings.png',dpi=50)
print('max d of scan points near axis',d[near&(np.hypot(q1,q2)<45)].max())
np.save('endframe.npy',np.stack([c0,T,e1,e2]))
