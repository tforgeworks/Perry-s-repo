import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, matplotlib.cm as cm, render
from scipy.spatial import cKDTree
A=np.load('final_samples.npy'); t=cKDTree(A[:,:3])
P=np.load('outerP.npy')[::4].astype(float); N=np.load('outerN.npy')[::4]
dd,_=t.query(P,workers=4)
C=cm.viridis(np.clip(dd/1.0,0,1))[:,:3]
vl=[([0,0,-1],[0,1,0],'top'),([0,0,1],[0,1,0],'bottom'),([0,1,0],[0,0,1],'side'),([0,-1,0],[0,0,1],'other side')]
fig,ax=plt.subplots(1,4,figsize=(24,6.5))
for a,(d,u,tt) in zip(ax,vl):
    a.imshow(np.clip(render.render_col(P,N,C,d,u,0.6),0,1)); a.set_title(tt,fontsize=14); a.axis('off')
sm=cm.ScalarMappable(cmap='viridis',norm=matplotlib.colors.Normalize(0,1)); sm.set_array([])
cb=fig.colorbar(sm,ax=ax,fraction=0.015,pad=0.01); cb.set_label('distance from scan point to repaired model (mm), clipped at 1 mm',fontsize=12)
fig.suptitle('Scan vs repaired model. Yellow = rebuilt outlet (broken in the scan); purple = matches the scan',fontsize=15)
plt.savefig('deviation.png',dpi=70,bbox_inches='tight')
