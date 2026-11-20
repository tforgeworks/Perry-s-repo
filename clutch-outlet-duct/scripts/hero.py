import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, render
A=np.load('final_samples.npy'); S=A[:,:3]; SN=A[:,3:]
P=np.load('P.npy')[::2]; N=np.load('PN.npy')[::2]
c0,T,e1,e2=np.load('endframe.npy')
views=[(np.array([0.3,-0.5,-0.8]),[0,1,0],'top'),(np.array([0.2,0.9,0.3]),[0,0,1],'outlet side'),(np.array([-0.4,-0.3,0.85]),[0,1,0],'mouth'),(-T,e2,'into outlet')]
fig,ax=plt.subplots(2,4,figsize=(24,12))
for j,(d,up,t) in enumerate(views):
    ax[0,j].imshow(render.render_dir(P,N,d,up,0.35),cmap='gray',vmin=0,vmax=1); ax[0,j].set_title('scan (broken): '+t,fontsize=14)
    ax[1,j].imshow(render.render_dir(S,SN,d,up,0.35),cmap='gray',vmin=0,vmax=1); ax[1,j].set_title('repaired model: '+t,fontsize=14)
for a in ax.flat: a.axis('off')
plt.tight_layout(); plt.savefig('compare.png',dpi=80)
