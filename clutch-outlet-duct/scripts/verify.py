import numpy as np, trimesh, json, render
from scipy.spatial import cKDTree
A=np.load('pca_T.npy'); c=A[0]; vt=A[1:]
v=np.load('final_v.npy'); f=np.load('final_f.npy')
m=trimesh.Trimesh(v,f,process=False)
# work in PCA frame for analysis
mp=trimesh.Trimesh((v-c)@vt.T,f,process=False)
S,fi=trimesh.sample.sample_surface_even(mp,6_000_000) if False else mp.sample(6_000_000,return_index=True)
SN=mp.face_normals[fi]
np.save('final_samples.npy',np.c_[S,SN].astype(np.float32))
tree=cKDTree(S)
P=np.load('outerP.npy')[::6].astype(float)
dd,ii=tree.query(P,workers=4)
sd=np.einsum('ij,ij->i',P-S[ii],SN[ii])   # + means scan point outside model
p=json.load(open('params.json')); c0=np.load('endframe.npy')[0]
rep=np.linalg.norm(P-c0,axis=1)<95   # repaired outlet zone
def st(x): return dict(n=int(len(x)),mean=float(np.mean(x)),median_abs=float(np.median(np.abs(x))),p95_abs=float(np.percentile(np.abs(x),95)),rms=float(np.sqrt(np.mean(x**2))))
out={'scan_to_model_outside_repair_zone':st(sd[~rep]),'scan_to_model_in_repair_zone':st(sd[rep])}
print(json.dumps(out,indent=1))
json.dump(out,open('verify.json','w'),indent=1)
# deviation-colored render
dev=np.clip(np.abs(sd),0,1.5)/1.5
import matplotlib.cm as cm
C=cm.viridis(dev)[:,:3]
N=np.load('outerN.npy')[::6]
render.views_col(P,N,C,'deviation.png',[([0,0,-1],[0,1,0]),([0,0,1],[0,1,0]),([0,1,0],[0,0,1]),([0,-1,0],[0,0,1])],res=0.8,titles=['top','bottom','side','other side'])
