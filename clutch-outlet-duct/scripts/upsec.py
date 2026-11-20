import numpy as np, json
from scipy import ndimage as ndi
E=np.load('sdf_s.npy',mmap_mode='r'); g=np.load('grid.npy'); lo=g[:3];h=g[3]
PAR=json.load(open('params_in.json'))
c0,T,e1,e2=np.load('endframe.npy')
cc=c0+PAR['cuff_center_offset_e1']*e1+PAR['cuff_center_offset_e2']*e2
e1=np.cross(T,[0,0,1.]);e1/=np.linalg.norm(e1);e2=np.cross(T,e1)
d0=PAR['d0']
gx=np.arange(-70,70,0.25); U,V=np.meshgrid(gx,gx,indexing='ij')
X=cc+d0*T+U[...,None]*e1+V[...,None]*e2
c=((X-lo)/h-0.5).reshape(-1,3); a=np.floor(c.min(0)).astype(int)-2; b=np.ceil(c.max(0)).astype(int)+2
sub=np.asarray(E[a[0]:b[0],a[1]:b[1],a[2]:b[2]])
f=ndi.map_coordinates(sub,(c-a).T,order=1,cval=5).reshape(U.shape)
lab,_=ndi.label(f<0); sizes=ndi.sum(np.ones_like(f),lab,range(1,lab.max()+1)); m=lab==(np.argmax(sizes)+1)
cu=np.array([U[m].mean(),V[m].mean()])
ang=np.arctan2(V[m]-cu[1],U[m]-cu[0]); rho=np.hypot(U[m]-cu[0],V[m]-cu[1])
nb=360; b_=((ang+np.pi)/(2*np.pi)*nb).astype(int)%nb
R=np.zeros(nb); np.maximum.at(R,b_,rho)
R=ndi.uniform_filter1d(ndi.maximum_filter1d(R,3,mode='wrap'),5,mode='wrap')
print('up center (e1,e2)',cu.round(2),'R min/max',R.min().round(1),R.max().round(1),'area',m.sum()*0.0625)
np.save('upsec.npy',np.r_[cu,R]); np.save('upframe.npy',np.stack([cc,T,e1,e2]))
