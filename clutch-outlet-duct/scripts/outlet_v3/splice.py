# Splice the corrected outlet end onto the revised v2 model: everything beyond the cut in the tube is kept unchanged.
import numpy as np, trimesh, manifold3d as m3, json, sys
from sweepeval import ss, Lc, Tc
S_CUT=float(sys.argv[1]) if len(sys.argv)>1 else 80.0; OVER=0.3
Apc=np.load('pca_T.npy')
def toM(m): return m3.Manifold(m3.Mesh(vert_properties=np.asarray(m.vertices,np.float32),tri_verts=np.asarray(m.faces,np.uint32)))
def toT(M):
    q=M.to_mesh(); return trimesh.Trimesh(np.asarray(q.vert_properties)[:,:3],np.asarray(q.tri_verts),process=True)
v2=trimesh.load('/home/user/Perry-s-repo/clutch-outlet-duct/polaris_5439157_outlet_duct_revised_v2.stl'); v2.vertices=(v2.vertices-Apc[0])@Apc[1:].T
end=trimesh.load('end_piece.ply')
i=np.abs(ss-S_CUT).argmin(); o=Lc[i]; tb=Tc[i]/np.linalg.norm(Tc[i])
Mv=toM(v2); Me=toM(end); print('status',Mv.status(),Me.status())
keep=Mv.trim_by_plane(tuple(tb),float(o@tb))
new=Me.trim_by_plane(tuple(-tb),float(-(o@tb)-OVER))
print('kept part volume',round(keep.volume()),'new end volume',round(new.volume()))
U=keep+new
print('union: status',U.status(),'volume',round(U.volume()),'genus',U.genus(),'bodies',len(U.decompose()),'tris',U.num_tri())
m=toT(U); print('trimesh: watertight',m.is_watertight,'winding',m.is_winding_consistent,'bodies',m.body_count,'faces',len(m.faces))
# mismatch of the two pieces at the cut: distance between their surfaces in a 2 mm slab
from scipy.spatial import cKDTree
A_=v2.sample(2000000); B_=end.sample(800000)
ka=np.abs((A_-o)@tb)<1.0; kb=np.abs((B_-o)@tb)<1.0
d,_=cKDTree(A_[ka]).query(B_[kb]); print('surface mismatch at the cut: median %.3f p95 %.3f max %.3f mm'%(np.median(d),np.percentile(d,95),d.max()))
m.export('v3_pca.ply'); json.dump({'s_cut':S_CUT,'cut_point':o.tolist(),'cut_normal_toward_box':tb.tolist()},open('splice.json','w'))
