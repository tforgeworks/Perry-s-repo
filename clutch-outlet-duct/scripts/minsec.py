import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import minimize
from skimage import measure
F=np.asarray(np.load('sdf_s.npy',mmap_mode='r')); g=np.load('grid.npy'); lo=g[:3]; h=g[3]
CL=np.load('centerline.npy'); L=CL[:,:3];T=CL[:,3:6];arc=CL[:,6]
R=50; st=0.5; gx=np.arange(-R,R+st,st); U,V=np.meshgrid(gx,gx,indexing='ij')
def frame(t):
    t=t/np.linalg.norm(t); e1=np.cross(t,[0,0,1.]); 
    if np.linalg.norm(e1)<1e-3: e1=np.cross(t,[0,1.,0])
    e1/=np.linalg.norm(e1); return t,e1,np.cross(t,e1)
def section(c,t):
    t,e1,e2=frame(t)
    Xp=c+U[...,None]*e1+V[...,None]*e2
    f=ndi.map_coordinates(F,((Xp-lo)/h-0.5).reshape(-1,3).T,order=1,cval=10).reshape(U.shape)
    lab,_=ndi.label(f<0)
    k=lab[np.abs(gx).argmin(),np.abs(gx).argmin()]
    if k==0:
        # nearest component to center
        d=ndi.distance_transform_edt(lab==0,return_indices=True)[1]
        k=lab[tuple(d[:,len(gx)//2,len(gx)//2])]
    m=lab==k
    return m,e1,e2
def area(c,t): return section(c,t)[0].sum()*st*st
out=[]
for s in [70,62,55,48,42,36,30,25,20,15]:
    i=np.abs(arc-s).argmin(); c=L[i].copy(); t=T[i].copy()
    for it in range(3):
        def obj(ang):
            t_,e1,e2=frame(t); d=t_+ang[0]*e1+ang[1]*e2
            return area(c,d)
        r=minimize(obj,[0,0],method='Nelder-Mead',options={'xatol':1e-3,'fatol':1,'initial_simplex':[[0,0],[0.15,0],[0,0.15]]})
        t_,e1,e2=frame(t); t=t_+r.x[0]*e1+r.x[1]*e2; t/=np.linalg.norm(t)
        m,e1,e2=section(c,t)
        ij=np.argwhere(m).mean(0); c=c+(gx[0]+ij[0]*st)*e1+(gx[0]+ij[1]*st)*e2
    m,e1,e2=section(c,t)
    cs=measure.find_contours(np.where(m,-1.,1.),0); per=max(np.sum(np.linalg.norm(np.diff(q,axis=0),axis=1)) for q in cs)*st
    rp=measure.regionprops(m.astype(int))[0]
    out.append(np.r_[s,c,t,m.sum()*st*st,per,rp.axis_major_length*st,rp.axis_minor_length*st])
    print(s,'c',c.round(1),'t',t.round(3),'area',round(m.sum()*st*st),'per',round(per,1),'Deq',round(per/np.pi,1),'maj/min',round(rp.axis_major_length*st,1),round(rp.axis_minor_length*st,1),flush=True)
np.save('minsec.npy',np.array(out))
