import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy import ndimage as ndi
from scipy.interpolate import splprep, splev
from skimage import measure
F=np.load('sdf_s.npy',mmap_mode='r'); g=np.load('grid.npy'); lo=g[:3]; h=g[3]
C=np.load('centerline_raw.npy')
tck,u=splprep(C.T,s=len(C)*4.0)
uu=np.linspace(0,1,600); L=splev(uu,tck); D=splev(uu,tck,der=1)
L=np.array(L).T; T=np.array(D).T; T/=np.linalg.norm(T,axis=1,keepdims=True)
arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(L,axis=0),axis=1))]
np.save('centerline.npy',np.c_[L,T,arc])
print('total length',arc[-1])
R=55; st=0.35; gx=np.arange(-R,R+st,st)
U,V=np.meshgrid(gx,gx,indexing='ij')
rows=[]
Fa=np.asarray(F)
for i in range(0,600,6):
    t=T[i]; e1=np.cross(t,[0,0,1.]); e1/=np.linalg.norm(e1); e2=np.cross(t,e1)
    Xp=L[i]+U[...,None]*e1+V[...,None]*e2
    c=((Xp-lo)/h-0.5).reshape(-1,3).T
    f=ndi.map_coordinates(Fa,c,order=1,cval=10).reshape(U.shape)
    lab,_=ndi.label(f<0); k=lab[len(gx)//2,len(gx)//2]
    if k==0: rows.append([arc[i]]+[np.nan]*5); continue
    m=lab==k; area=m.sum()*st*st
    cs=measure.find_contours(np.where(m,-1.,1.),0)
    per=max(np.sum(np.linalg.norm(np.diff(c_,axis=0),axis=1)) for c_ in cs)*st
    rp=measure.regionprops(m.astype(int))[0]
    rows.append([arc[i],area,per,per/np.pi,rp.major_axis_length*st,rp.minor_axis_length*st])
rows=np.array(rows); np.save('xsec.npy',rows)
fig,ax=plt.subplots(1,2,figsize=(14,5))
ax[0].plot(rows[:,0],rows[:,3],label='perimeter/pi'); ax[0].plot(rows[:,0],2*np.sqrt(rows[:,1]/np.pi),label='area-equiv D')
ax[0].plot(rows[:,0],rows[:,4],label='major');ax[0].plot(rows[:,0],rows[:,5],label='minor');ax[0].legend();ax[0].grid();ax[0].set_xlabel('arc from outlet end (mm)')
ax[1].plot(L[:,0],L[:,1]);ax[1].set_aspect('equal')
plt.savefig('xsec.png',dpi=70)
for r in rows[:40]: print(np.round(r,1))
