import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
def rotmat(az,el):
    a,e=np.radians(az),np.radians(el)
    Rz=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
    Rx=np.array([[1,0,0],[0,np.cos(e),-np.sin(e)],[0,np.sin(e),np.cos(e)]])
    return Rx@Rz
def render(P,N,az,el,res=0.35,light=(0.3,0.5,1.0)):
    # view: camera looks along -z after rotation; x right, y up
    R=rotmat(az,el); Q=P@R.T; M=N@R.T
    x=Q[:,0];y=Q[:,2];z=-Q[:,1]  # el rotates; look along +y
    ix=((x-x.min())/res).astype(int); iy=((y.max()-y)/res).astype(int)
    W,H=ix.max()+1,iy.max()+1
    key=iy*W+ix
    o=np.lexsort((z,key)); k=key[o]; first=np.r_[True,k[1:]!=k[:-1]]
    sel=o[first]
    L=np.array(light,float); L/=np.linalg.norm(L)
    n=M[sel]; nn=np.stack([n[:,0],n[:,2],-n[:,1]],1)
    s=np.abs(nn@np.array([L[0],L[1],-L[2]]))*0.8+0.2
    img=np.ones(H*W); img[k[first]]=s
    return img.reshape(H,W)
def views(P,N,out,vlist,res=0.35,titles=None):
    fig,ax=plt.subplots(1,len(vlist),figsize=(6*len(vlist),6))
    ax=np.atleast_1d(ax)
    for a,(az,el) in zip(ax,vlist):
        a.imshow(render(P,N,az,el,res),cmap='gray',vmin=0,vmax=1); a.set_title(f'az{az} el{el}'); a.axis('off')
    plt.tight_layout(); plt.savefig(out,dpi=70)

def render_dir(P,N,d,up,res=0.3,light=None):
    d=np.asarray(d,float);d/=np.linalg.norm(d)
    up=np.asarray(up,float);r=np.cross(d,up);r/=np.linalg.norm(r);u=np.cross(r,d)
    x=P@r;y=P@u;z=P@d
    ix=((x-x.min())/res).astype(int); iy=((y.max()-y)/res).astype(int)
    W,H=ix.max()+1,iy.max()+1; key=iy*W+ix
    o=np.lexsort((z,key)); k=key[o]; first=np.r_[True,k[1:]!=k[:-1]]; sel=o[first]
    L=-d+0.5*u+0.3*r if light is None else np.asarray(light,float); L/=np.linalg.norm(L)
    s=np.abs(N[sel]@L)*0.8+0.2
    img=np.ones(H*W); img[k[first]]=s
    return img.reshape(H,W)
def views_dir(P,N,out,vlist,res=0.3,titles=None):
    fig,ax=plt.subplots(1,len(vlist),figsize=(6*len(vlist),6)); ax=np.atleast_1d(ax)
    for i,(a,(d,up)) in enumerate(zip(ax,vlist)):
        a.imshow(render_dir(P,N,d,up,res),cmap='gray',vmin=0,vmax=1); a.axis('off')
        a.set_title(titles[i] if titles else f'view {np.round(d,2)}')
    plt.tight_layout(); plt.savefig(out,dpi=70)

def render_col(P,N,C,d,up,res=0.8):
    d=np.asarray(d,float);d/=np.linalg.norm(d)
    up=np.asarray(up,float);r=np.cross(d,up);r/=np.linalg.norm(r);u=np.cross(r,d)
    x=P@r;y=P@u;z=P@d
    ix=((x-x.min())/res).astype(int); iy=((y.max()-y)/res).astype(int)
    W,H=ix.max()+1,iy.max()+1; key=iy*W+ix
    o=np.lexsort((z,key)); k=key[o]; first=np.r_[True,k[1:]!=k[:-1]]; sel=o[first]
    L=-d+0.5*u+0.3*r; L/=np.linalg.norm(L)
    s=np.abs(N[sel]@L)*0.7+0.3
    img=np.ones((H*W,3)); img[k[first]]=C[sel]*s[:,None]
    return img.reshape(H,W,3)
def views_col(P,N,C,out,vlist,res=0.8,titles=None):
    fig,ax=plt.subplots(1,len(vlist),figsize=(6*len(vlist),6)); ax=np.atleast_1d(ax)
    for i,(a,(d,up)) in enumerate(zip(ax,vlist)):
        a.imshow(np.clip(render_col(P,N,C,d,up,res),0,1)); a.axis('off'); a.set_title(titles[i] if titles else str(np.round(d,2)))
    plt.tight_layout(); plt.savefig(out,dpi=70)
