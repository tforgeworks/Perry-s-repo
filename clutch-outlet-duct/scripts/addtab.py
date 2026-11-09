# Add the outlet-rim keying tab: a flat radial tab on the outer side of the bend,
# just behind the cuff end (shape and position from photos of the OEM part).
import numpy as np, json
W=np.load('W3.npy'); g=np.load('grid.npy'); lo=g[:3]; h=g[3]
p=json.load(open('params.json')); cc=np.array(p['cuff_center']); T=np.array(p['cuff_axis'])
e1=np.cross(T,[0,0,1.]);e1/=np.linalg.norm(e1);e2=np.cross(T,e1)
TAB=dict(angle_deg=-140.0,radial_out_mm=7.0,axial_len_mm=10.0,thick_mm=3.0,gap_from_end_mm=4.0,edge_round_mm=1.0,fillet_mm=1.0)
Ro=p['Ro']; dend=p['d_end']
a=np.radians(TAB['angle_deg']); rad=np.cos(a)*e1+np.sin(a)*e2; tan=np.cross(T,rad)
d1=dend-TAB['gap_from_end_mm']; d0=d1-TAB['axial_len_mm']
r0=Ro-1.5; r1=Ro+TAB['radial_out_mm']
ctr=cc+T*(d0+d1)/2+rad*(r0+r1)/2
half=np.array([(d1-d0)/2,(r1-r0)/2,TAB['thick_mm']/2])
R=np.stack([T,rad,tan])
corner=[ctr+R.T@(half*s) for s in np.array(np.meshgrid([-1,1],[-1,1],[-1,1])).reshape(3,-1).T]
corner=np.array(corner); ia=np.maximum(np.floor((corner.min(0)-4-lo)/h).astype(int),0); ib=np.minimum(np.ceil((corner.max(0)+4-lo)/h).astype(int),W.shape)
assert (ib-ia>0).all()
idx=np.indices(ib-ia).reshape(3,-1).T+ia
X=(idx+0.5)*h+lo
q=(X-ctr)@R.T
rr=TAB['edge_round_mm']; qd=np.abs(q)-(half-rr)
box=np.linalg.norm(np.maximum(qd,0),axis=1)+np.minimum(qd.max(1),0)-rr
# keep the bore clear
v=X-cc; dd=v@T; radial=np.linalg.norm(v-np.outer(dd,T),axis=1)
box=np.maximum(box,(Ro-p['t_cuff'])-radial)
w=W[idx[:,0],idx[:,1],idx[:,2]]
k=TAB['fillet_mm']; hh=np.clip(0.5+0.5*(box-w)/k,0,1)
smin=box*(1-hh)+w*hh-k*hh*(1-hh)
W[idx[:,0],idx[:,1],idx[:,2]]=np.minimum(w,smin)
np.save('W4.npy',W)
p['rim_tab']=TAB|{'center_work_frame':ctr.tolist(),'radial_dir':rad.tolist()}
json.dump(p,open('params.json','w'),indent=1)
print('tab block',ia,ib,'grid',W.shape)
