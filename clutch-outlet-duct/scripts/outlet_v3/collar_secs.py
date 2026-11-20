import numpy as np, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
P=np.load('P.npy').astype(float)
z=np.load(sys.argv[1]); a=z['axis']/np.linalg.norm(z['axis']); c=z['center']
hp=np.load('hook_plane.npy'); n=hp[1]/np.linalg.norm(hp[1])
e1=n-(n@a)*a; e1/=np.linalg.norm(e1); e2=np.cross(a,e1)
k=np.linalg.norm(P-c,axis=1)<80; Q=P[k]; v=Q-c; d=v@a
fig,ax=plt.subplots(2,6,figsize=(48,16))
for A,ang in zip(ax.flat,range(0,180,15)):
    t=np.radians(ang); u=np.cos(t)*e1+np.sin(t)*e2; w=np.cross(a,u)
    s=np.abs(v@w)<0.25
    A.plot(v[s]@u,d[s],',k'); A.set_aspect('equal'); A.set_xlim(-75,75); A.set_ylim(-75,35); A.grid(alpha=.4)
    for r in (z['R'],-z['R']): A.axvline(r,color='r',lw=0.5)
    A.set_title(f'{ang} deg (0 = across hook plane, 90 = in hook plane)',fontsize=12)
plt.tight_layout(); plt.savefig(sys.argv[2],dpi=40)
