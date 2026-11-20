import numpy as np, trimesh, json, pymeshfix, manifold3d as m3
from scipy.spatial import cKDTree
from scipy import ndimage as ndi
from sweepeval import project
Apc=np.load('pca_T.npy'); p=json.load(open('end_params.json')); sp_=json.load(open('splice.json'))
A=np.array(p['A']); c=np.array(p['c'])
m=trimesh.load('v3_pca.ply')
mf=pymeshfix.MeshFix(np.asarray(m.vertices,float),np.asarray(m.faces,np.int32)); mf.repair()
mo=trimesh.Trimesh(mf.points if hasattr(mf,'points') else mf.v, mf.faces if hasattr(mf,'faces') else mf.f,process=True)
if mo.volume<0: mo.invert()
e=mo.edges_sorted; u,cn=np.unique(e,axis=0,return_counts=True)
info=dict(faces=len(mo.faces),watertight=bool(mo.is_watertight),bodies=int(mo.body_count),boundary_edges=int((cn==1).sum()),nonmanifold_edges=int((cn>2).sum()),volume_cm3=round(float(mo.volume)/1000,1),
          extents_aligned_mm=[round(float(x),1) for x in mo.vertices.max(0)-mo.vertices.min(0)],units='mm',frame='same coordinates as Mesh_Tressa.stl')
print(info)
out={}
# step at the splice
v2=trimesh.load('/home/user/Perry-s-repo/clutch-outlet-duct/polaris_5439157_outlet_duct_revised_v2.stl'); v2.vertices=(v2.vertices-Apc[0])@Apc[1:].T
end=trimesh.load('end_piece.ply'); o=np.array(sp_['cut_point']); tb=np.array(sp_['cut_normal_toward_box'])
B=end.sample(600000); B=B[np.abs((B-o)@tb)<1.5]; fc=v2.triangles_center; sub=v2.submesh([np.where(np.abs((fc-o)@tb)<6)[0]],append=True)
_,d,_=trimesh.proximity.closest_point(sub,B[:20000]); out['step_at_splice_mm']=dict(median=round(float(np.median(d)),3),p95=round(float(np.percentile(d,95)),3),max=round(float(d.max()),3)); print('splice',out['step_at_splice_mm'])
# unchanged part: identical to v2 beyond the cut
S,fi=mo.sample(5_000_000,return_index=True); SN=mo.face_normals[fi]; t=cKDTree(S)
Sv=v2.sample(400000); Sv=Sv[(Sv-o)@tb>2.0]; dv,_=t.query(Sv,workers=-1); out['unchanged_part_vs_v2_mm']=dict(max=round(float(dv.max()),3)); print('unchanged part vs v2: max %.3f mm'%dv.max())
# scan vs model around the elbow
P=np.load('outerP.npy')[::3].astype(float); X=P-c; near=np.linalg.norm(X,axis=1)<95; P=P[near]; X=X[near]; d_=X@A
s,_,_=project(P); dd,ii=t.query(P,workers=-1)
for name,k in [('tube leading into the elbow',s>=66),('elbow body (dome)',(s<66)&(d_<3)),('outlet cuff',(s<66)&(d_>=3))]:
    x=dd[k]; out[name]=dict(scan_points=int(k.sum()),median_mm=round(float(np.median(x)),2),p90_mm=round(float(np.percentile(x,90)),2),within_0_5mm=round(float((x<0.5).mean()),3),within_1mm=round(float((x<1).mean()),3),further_than_3mm=round(float((x>3).mean()),3)); print(name,out[name])
# wall thickness of the rebuilt end (voxel field)
W=np.load('end_W.npy'); fo2=np.load('end_fo2.npy'); h=float(np.load('grid.npy')[3])
dout=ndi.distance_transform_edt(fo2<0)*h; inner=(np.abs(W)<0.25)&(fo2<-1.0); th=dout[inner]
out['rebuilt_end_wall_mm']=dict(p1=round(float(np.percentile(th,1)),2),p5=round(float(np.percentile(th,5)),2),median=round(float(np.median(th)),2),p95=round(float(np.percentile(th,95)),2)); print('wall',out['rebuilt_end_wall_mm'])
M=m3.Manifold(m3.Mesh(vert_properties=np.asarray(mo.vertices,np.float32),tri_verts=np.asarray(mo.faces,np.uint32))); info['manifold_status']=str(M.status())
out['mesh']=info; out['outlet']=dict(cuff_outside_diameter_mm=2*p['R'],cuff_inside_diameter_mm=2*p['R_in'],cuff_wall_mm=p['R']-p['R_in'],rim_outside_diameter_mm=2*(p['R']+p['bead_out']),cuff_length_rim_to_tube_mm=p['d_rim'],cuff_axis=p['A'],cuff_center=p['c'],old_axis_error_deg=round(float(np.degrees(np.arccos(np.clip(A@np.array([0.5604,0.8013,-0.2092]),-1,1)))),1))
json.dump(out,open('verify_v3.json','w'),indent=1)
mo.export('v3_pca_fixed.ply'); ms=mo.copy(); ms.vertices=mo.vertices@Apc[1:]+Apc[0]; ms.export('final_export_v3.stl'); print('exported; old axis error',out['outlet']['old_axis_error_deg'])
