import numpy as np, json, trimesh, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_rgb
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
SURF='#fcfcfb'; INK='#0b0b0b'; INK2='#52514e'; MUTED='#898781'; GRID='#e1e0d9'
SCAN='#eb6834'; MODEL='#2a78d6'
DIV=LinearSegmentedColormap.from_list('div',['#0d366b','#184f95','#3987e5','#9ec5f4','#f0efec','#f2b0ae','#e34948','#b02a2a','#7d1616'])
plt.rcParams.update({'font.family':'DejaVu Sans','text.color':INK,'axes.labelcolor':INK2,'xtick.color':MUTED,'ytick.color':MUTED,'axes.edgecolor':'#c3c2b7','figure.facecolor':SURF,'axes.facecolor':SURF,'savefig.facecolor':SURF})
Z=np.load('superimpose.npz'); P=Z['P'].astype(float); PN=Z['PN'].astype(float); sd=Z['sd']; S=Z['S'].astype(float); SN=Z['SN'].astype(float)
st=json.load(open('superimpose.json')); p=json.load(open('end_params.json')); A=np.array(p['A']); c=np.array(p['c']); tv=np.array(p['toward_tube_dir'])
def basis(d,up):
    d=np.asarray(d,float); d/=np.linalg.norm(d); up=np.asarray(up,float); r=np.cross(d,up); r/=np.linalg.norm(r); u=np.cross(r,d); return d,r,u
def splat(pts,nrm,col,d,up,res,bounds,lo=0.5,hi=0.5):
    d,r,u=basis(d,up); x=pts@r; y=pts@u; z=pts@d; x0,x1,y0,y1=bounds
    W=int((x1-x0)/res)+1; H=int((y1-y0)/res)+1
    ix=((x-x0)/res).astype(int); iy=((y1-y)/res).astype(int); ok=(ix>=0)&(ix<W)&(iy>=0)&(iy<H)
    key=iy[ok]*W+ix[ok]; zz=z[ok]; o=np.lexsort((zz,key)); kk=key[o]; first=np.r_[True,kk[1:]!=kk[:-1]]; sel=np.where(ok)[0][o[first]]
    L=-d+0.5*u+0.3*r; L/=np.linalg.norm(L); sh=lo+hi*np.abs(nrm[sel]@L)
    img=np.tile(np.array(to_rgb(SURF)),(H*W,1)); img[kk[first]]=col[sel]*sh[:,None]; return img.reshape(H,W,3)
def bounds_of(d,up,sets,pad=6):
    d,r,u=basis(d,up); xs=np.concatenate([q@r for q in sets]); ys=np.concatenate([q@u for q in sets]); return xs.min()-pad,xs.max()+pad,ys.min()-pad,ys.max()+pad
norm=Normalize(-1.5,1.5)
def figure(P_,PN_,sd_,S_,SN_,views,names,res,title,sub,out,figw):
    Cdev=DIV(norm(np.clip(sd_,-1.5,1.5)))[:,:3]
    bP=np.r_[P_,S_]; bN=np.r_[PN_,SN_]; bC=np.r_[np.tile(np.array(to_rgb(SCAN)),(len(P_),1)),np.tile(np.array(to_rgb(MODEL)),(len(S_),1))]
    n=len(views); B=[list(bounds_of(d,u,[P_,S_])) for d,u in views]
    hmax=max(b[3]-b[2] for b in B)
    for b in B: mid=(b[2]+b[3])/2; b[2]=mid-hmax/2; b[3]=mid+hmax/2          # same height for every view, so the rows line up
    wr=[b[1]-b[0] for b in B]; HEAD=1.95; FOOT=1.05; rowh=figw*0.95*hmax/sum(wr)
    figh=2*rowh+HEAD+FOOT+0.25
    fig=plt.figure(figsize=(figw,figh)); gs=fig.add_gridspec(2,n,width_ratios=wr,left=0.025,right=0.975,top=1-HEAD/figh,bottom=FOOT/figh,wspace=0.02,hspace=0.25/rowh)
    for j,((d,u),nm) in enumerate(zip(views,names)):
        a=fig.add_subplot(gs[0,j]); a.imshow(splat(bP,bN,bC,d,u,res,B[j],0.55,0.45)); a.set_title(nm,fontsize=13,color=INK2,pad=4); a.axis('off')
        a=fig.add_subplot(gs[1,j]); a.imshow(splat(P_,PN_,Cdev,d,u,res,B[j],0.72,0.28)); a.axis('off')
    fig.text(0.025,1-0.38/figh,title,fontsize=19,fontweight='bold',color=INK,va='top'); fig.text(0.025,1-0.82/figh,sub,fontsize=12.5,color=INK2,va='top')
    fig.legend(handles=[Patch(color=SCAN,label='Scan of the original'),Patch(color=MODEL,label='Model (revised v3)')],loc='upper left',bbox_to_anchor=(0.018,1-1.12/figh),ncol=2,frameon=False,fontsize=12.5,handlelength=1.2,columnspacing=1.6)
    fig.text(0.285,1-1.33/figh,'Top row: both drawn together; whichever surface is outermost shows, even by a few hundredths of a mm. Solid blue also marks areas with no scan. The bottom row shows by how much.',fontsize=11.5,color=INK2,va='center')
    cax=fig.add_axes([0.30,0.56/figh,0.40,0.16/figh]); cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=DIV),cax=cax,orientation='horizontal',ticks=[-1.5,-1,-0.5,0,0.5,1,1.5]); cb.outline.set_edgecolor('#c3c2b7'); cb.ax.tick_params(labelsize=11,length=3)
    cb.ax.set_xticklabels(['≤ −1.5','−1','−0.5','0','0.5','1','≥ 1.5'])
    fig.text(0.295,0.64/figh,'model stands proud',ha='right',va='center',fontsize=11.5,color=INK2); fig.text(0.705,0.64/figh,'scan stands proud',ha='left',va='center',fontsize=11.5,color=INK2)
    fig.text(0.5,0.14/figh,'Bottom row: each scan point colored by its distance to the model surface (mm)',ha='center',fontsize=11.5,color=INK2)
    fig.savefig(out,dpi=110); plt.close(fig)
al=st['all']; bx=st['Box, mouth and mounting ear']; tb=st['Tube']; bf=st['best_fit_correction_on_box_and_tube']
mesh0=trimesh.load('v3_pca_fixed.ply'); S7,f7=mesh0.sample(7_500_000,return_index=True); SN7=mesh0.face_normals[f7]
figure(P,PN,sd,S7,SN7,[([0,0,-1],[0,1,0]),([0,0,1],[0,1,0]),([0,1,0],[0,0,1]),([0,-1,0],[0,0,1])],['Top','Bottom','Side','Other side'],0.55,
 'The scan and the model coincide: %.0f%% of the scan lies within 1 mm of the model'%(100*al['within_1mm']),
 'Box, mouth and ear: %.1f%% within 0.5 mm. Tube: %.1f%%. No re-alignment was applied; a best-fit correction would move no point more than %.2f mm.'%(100*bx['within_0_5mm'],100*tb['within_0_5mm'],bf['largest_point_shift_mm']),
 'superimpose_overview.png',22)
# outlet end, at full scan density
from scipy.spatial import cKDTree
side=np.cross(A,tv); mesh=trimesh.load('v3_pca_fixed.ply')
Pf=np.load('P.npy').astype(float); PNf=np.load('PN.npy').astype(float)
ke=np.linalg.norm(Pf-c,axis=1)<100; Pe=Pf[ke]; PNe=PNf[ke]
sub=mesh.submesh([np.where(np.linalg.norm(mesh.triangles_center-c,axis=1)<112)[0]],append=True)
Se,fi=sub.sample(3_500_000,return_index=True); SNe=sub.face_normals[fi]
dd,ii=cKDTree(Se).query(Pe,workers=-1); pl=np.einsum('ij,ij->i',Pe-Se[ii],SNe[ii]); sde=np.sign(pl)*np.where((dd<1.0)&(np.abs(pl)<=dd+0.05),np.abs(pl),dd)
km=np.linalg.norm(Se-c,axis=1)<100
eb=st['Elbow at the outlet end']; cf=st['Outlet cuff']
figure(Pe,PNe,sde,Se[km],SNe[km],[(side,A),(-side,A),(tv,A),(-A,side)],['One side','Other side','Outside of the elbow','Looking into the opening'],0.27,
 'Outlet end: the elbow matches where the original survives (%.0f%% within 1 mm)'%(100*eb['within_1mm']),
 'Colored patches are burned, melted or rebuilt areas. The cuff matches less (%.0f%% within 1 mm) because the scanned rim is oval and curled from the heat, and the model is round.'%(100*cf['within_1mm']),
 'superimpose_outlet.png',22)
# ---------------- cross-sections
from sweepeval import ss,Lc,Tc
mp=np.load('mirror_plane.npz'); mm=mp['m']/np.linalg.norm(mp['m']); moff=float(mp['off'])
def fr(n,hint):
    n=np.asarray(n,float); n/=np.linalg.norm(n); a=np.asarray(hint,float); a=a-(a@n)*n; a/=np.linalg.norm(a); return n,a,np.cross(n,a)
i160=np.abs(ss-160).argmin(); i95=np.abs(ss-95).argmin()
secs=[('A  Box and mouth',np.array([-150.,0,0]),*fr([1,0,0],[0,1,0]),None),
      ('B  Where the tube leaves the box',np.array([-70.,0,0]),*fr([1,0,0],[0,1,0]),None),
      ('C  Tube, middle',Lc[i160],*fr(Tc[i160],[0,0,1]),60),
      ('D  Tube, just before the elbow',Lc[i95],*fr(Tc[i95],[0,0,1]),60),
      ('E  Elbow and cuff, cut lengthwise',c+moff*mm-A*18+tv*14,*fr(mm,tv),88),
      ('F  Cuff, cut across',c+A*12,*fr(A,tv),52)]
fig,axs=plt.subplots(2,3,figsize=(20,13.6)); fig.subplots_adjust(left=0.045,right=0.985,top=0.875,bottom=0.055,wspace=0.14,hspace=0.2)
for a,(nm,o,n,u,v,rad) in zip(axs.flat,secs):
    k=np.abs((Pf-o)@n)<0.15; q=Pf[k]-o
    if rad: q=q[np.linalg.norm(q,axis=1)<rad*1.5]
    a.scatter(q@u,q@v,s=7,color=SCAN,alpha=0.55,linewidths=0,zorder=2)
    sec=mesh.section(plane_origin=o,plane_normal=n)
    for e in sec.discrete:
        w=e-o
        if rad and np.linalg.norm(w,axis=1).min()>rad*1.5: continue
        a.plot(w@u,w@v,color=MODEL,lw=1.3,zorder=3)
    a.set_aspect('equal'); a.grid(color=GRID,lw=0.8,zorder=0); a.set_axisbelow(True)
    if rad: a.set_xlim(-rad,rad); a.set_ylim(-rad,rad)
    else:
        xs=q@u; ys=q@v; a.set_xlim(xs.min()-8,xs.max()+8); a.set_ylim(ys.min()-8,ys.max()+8)
    a.set_title(nm,fontsize=14,color=INK,loc='left',pad=8); a.tick_params(labelsize=10.5,length=0)
    for sp in a.spines.values(): sp.set_visible(False)
    a.set_xlabel('mm',fontsize=10.5,loc='right')
fig.text(0.045,0.972,'Cross-sections: the model outline runs through the scan points',fontsize=19,fontweight='bold',va='top')
fig.text(0.045,0.940,'Six cuts through the scan and the model in the same position. In E the left of the elbow has no scan points: that is the burned-through patch. In F the scanned cuff is oval; the model is round.',fontsize=12.5,color=INK2,va='top')
fig.legend(handles=[Line2D([],[],marker='o',ls='',color=SCAN,alpha=0.7,markersize=8,label='Scan of the original (points within 0.15 mm of the cut)'),Line2D([],[],color=MODEL,lw=2,label='Model (revised v3)')],loc='upper left',bbox_to_anchor=(0.04,0.925),ncol=2,frameon=False,fontsize=12.5,columnspacing=2)
fig.savefig('superimpose_sections.png',dpi=110); plt.close(fig)
print('figures done')
