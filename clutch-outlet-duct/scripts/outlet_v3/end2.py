# Corrected outlet end, step 2: clean the dome's outer surface (no crust, burn holes refilled smoothly),
# leaving the ideal collar and the sweep tube untouched. Result is a displacement applied to the field.
import numpy as np, json, time, trimesh, fast_simplification, scipy.sparse as sp, scipy.sparse.linalg as sla
from skimage import measure
from scipy.spatial import cKDTree
from sweepeval import project
t0=time.time()
p=json.load(open('end_params.json')); a=np.array(p['box_a']); A=np.array(p['A']); c=np.array(p['c'])
g=np.load('grid.npy'); lo=g[:3]; h=g[3]
fo=np.load('end_fo.npy')
# closed outer surface of the whole local box (capped at the box faces) so inside/outside is well defined later
v,f,_,_=measure.marching_cubes(np.pad(fo,1,constant_values=1.0),0.0); v=(v-1)*h+lo+a*h+h/2
v2,f2=fast_simplification.simplify(np.asarray(v,np.float32),np.asarray(f,np.int32),target_count=560000)
m=trimesh.Trimesh(v2,f2,process=True); m=max(m.split(only_watertight=False),key=lambda x:len(x.faces)); print('closed outer mesh watertight',m.is_watertight)
V=np.asarray(m.vertices,float).copy(); F=m.faces; n=len(V); N0=m.vertex_normals.copy()
print('outer mesh',n,'verts',len(F),'faces',time.time()-t0,flush=True)
X=V-c; d=X@A; rad=np.linalg.norm(X-np.outer(d,A),axis=1)
wz=np.clip((d-p['d_a'])/(p['d_b']-p['d_a']),0,1); wr=np.clip((p['R']+p['zone_r']-rad)/4.0,0,1); wcol=wz*wr
s,_,_=project(V)
wdome=np.clip((66-s)/6,0,1)*(1-np.clip(wcol*1.5,0,1))*np.clip((92-np.linalg.norm(X,axis=1))/8,0,1)
wfair=np.clip((76-s)/8,0,1)*np.clip((p['d_b']-0.4-d)/2.0,0,1)*np.clip((92-np.linalg.norm(X,axis=1))/8,0,1)
wfair=np.where(rad>p['R']+p['zone_r'],np.clip((76-s)/8,0,1)*np.clip((92-np.linalg.norm(X,axis=1))/8,0,1),wfair)
bnd=np.zeros(n,bool); e=m.edges_sorted; u,cn=np.unique(e,axis=0,return_counts=True); bnd[np.unique(u[cn==1])]=True
e1c=np.array(p['e1']); e2c=np.array(p['e2']); rvv=X-np.outer(d,A); theta=np.degrees(np.arctan2(rvv@e2c,rvv@e1c))
melt=np.zeros(n,bool)   # no forced sector in the wall-based collar frame; unscanned areas are refilled automatically      # sector where the wall melted (from the scan's unrolled collar map)
wdome=np.where(melt,np.clip((p['d_b']-0.4-d)/1.5,0,1)*np.clip((d+40)/3,0,1)*np.clip(np.minimum(theta+115,55-theta)/8,0,1),wdome); wdome_m=np.where(melt,1.0,0.0)*(wdome>0.98)
wdome[bnd]=0
Psc=np.load('P.npy')[::2].astype(float); mp=np.load('mirror_plane.npz'); mm=mp['m']; moff=float(mp['off'])
near_=np.linalg.norm(Psc-c,axis=1)<95; Pm=Psc[near_]-2*((Psc[near_]-c)@mm-moff)[:,None]*mm        # mirrored scan also counts as support
ds=np.minimum(cKDTree(Psc).query(V,workers=-1)[0],cKDTree(Pm).query(V,workers=-1)[0])
Aadj=sp.coo_matrix((np.ones(len(m.edges_unique)*2),(np.r_[m.edges_unique[:,0],m.edges_unique[:,1]],np.r_[m.edges_unique[:,1],m.edges_unique[:,0]])),shape=(n,n)).tocsr()
# ---- 1. refill no-scan patches with a minimum-bending surface
free=((wdome>0.98)&(ds>1.0))|(wdome_m>0)
# widen each refilled patch by 9 mm so its edge sits on intact wall, not on the curled, melted rim of a burn hole
seedv=np.where(free)[0]
if len(seedv):
    dfree,_=cKDTree(V[seedv]).query(V,workers=-1); free|=(dfree<9.0)&(wdome>0.98)
fr=np.where(free)[0]; fx=np.where(~free)[0]
def cot(x,y): return np.einsum('ij,ij->i',x,y)/np.maximum(np.linalg.norm(np.cross(x,y),axis=1),1e-12)
I=[];J=[];W=[]
for k in range(3):
    i,j,o=F[:,k],F[:,(k+1)%3],F[:,(k+2)%3]; w=np.clip(0.5*cot(V[i]-V[o],V[j]-V[o]),0,None); I+=[i,j]; J+=[j,i]; W+=[w,w]
Wm=sp.coo_matrix((np.concatenate(W),(np.concatenate(I),np.concatenate(J))),shape=(n,n)).tocsr()
L=sp.diags(np.asarray(Wm.sum(1)).ravel())-Wm
ar=np.linalg.norm(np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]]),axis=1)/6
M=np.bincount(F.ravel(),np.repeat(ar,3),n); Q=(L@sp.diags(1/np.maximum(M,1e-9))@L).tocsr()
solve=sla.factorized(Q[fr][:,fr].tocsc()); Qfx=Q[fr][:,fx]
V1=V.copy()
for k in range(3): V1[fr,k]=solve(-(Qfx@V[fx,k]))
mv=np.linalg.norm(V1-V,axis=1)[fr]; print('refilled no-scan vertices',len(fr),'moved median %.2f p95 %.2f max %.2f'%(np.median(mv),np.percentile(mv,95),mv.max()),time.time()-t0,flush=True)
# ---- 2. robust feature-preserving smoothing (crust off, shape kept)
RAD_=9.0; CLAMP=2.0
idx=np.where(wdome>0)[0]; Vc=V1.copy(); m.vertices=Vc; Nn=m.vertex_normals.copy()
for ps in range(2):
    tree=cKDTree(Vc); out=Vc.copy()
    for st in range(0,len(idx),4000):
        ii=idx[st:st+4000]; nb=tree.query_ball_point(Vc[ii],RAD_,workers=4)
        for k_,i in enumerate(ii):
            Jn=np.array(nb[k_]); n0=Nn[i]; Jn=Jn[Nn[Jn]@n0>0.8]
            if len(Jn)<12: continue
            b1=np.cross(n0,[1,0,0]); 
            if np.linalg.norm(b1)<0.1: b1=np.cross(n0,[0,1,0])
            b1/=np.linalg.norm(b1); b2=np.cross(n0,b1)
            q=Vc[Jn]-Vc[i]; x=q@b1; y=q@b2; zz=q@n0
            Am=np.stack([np.ones_like(x),x,y,x*x,x*y,y*y],1); ws=np.exp(-(x*x+y*y)/(2*(RAD_/2)**2)); wt=ws.copy()
            for it in range(4):
                sw=np.sqrt(wt); co,*_=np.linalg.lstsq(Am*sw[:,None],zz*sw,rcond=None)
                r=zz-Am@co; sc=max(1.4826*np.median(np.abs(r)),0.05); uu=r/(4*sc); wt=ws*np.where(np.abs(uu)<1,(1-uu*uu)**2,0)
            out[i]=Vc[i]+wdome[i]*np.clip(co[0],-CLAMP,CLAMP)*n0
    Vc=out; m.vertices=Vc; Nn=m.vertex_normals.copy(); print('smoothing pass',ps,time.time()-t0,flush=True)
# ---- final fairing of the whole dome (no real features there): smooth small creases, keep the size
wfair[bnd]=0
deg=np.maximum(np.asarray(Aadj.sum(1)).ravel(),1); Mavg=sp.diags(1/deg)@Aadj
ms=trimesh.Trimesh(Vc,F,process=False); trimesh.smoothing.filter_taubin(ms,lamb=0.5,nu=-0.53,iterations=120); Vs=ms.vertices
Dd=Vc-Vs
for i in range(300): Dd=0.5*Dd+0.5*(Mavg@Dd)
Vf=Vs+Dd; mvf=np.linalg.norm(Vf-Vc,axis=1)
Vc=Vc+wfair[:,None]*(Vf-Vc)
print('fairing moved: median %.3f p95 %.3f max %.3f'%(np.median(mvf[wfair>0.5]),np.percentile(mvf[wfair>0.5],95),(mvf*wfair).max()))
delta=np.einsum('ij,ij->i',Vc-V,N0)
print('total normal displacement on dome: median |d| %.2f p95 %.2f max %.2f'%(np.median(np.abs(delta[idx])),np.percentile(np.abs(delta[idx]),95),np.abs(delta).max()))
np.save('end_V0.npy',V); np.save('end_delta.npy',delta); np.save('end_Vclean.npy',Vc); np.save('end_F.npy',F)
