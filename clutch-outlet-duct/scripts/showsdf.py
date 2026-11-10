import numpy as np, sys, render
from skimage import measure
F=np.load(sys.argv[1],mmap_mode='r'); g=np.load('grid.npy')
s=int(sys.argv[3]) if len(sys.argv)>3 else 2
v,f,n,_=measure.marching_cubes(np.asarray(F[::s,::s,::s]),0)
v=v*g[3]*s+g[:3]+g[3]/2
np.save(sys.argv[2]+'_v.npy',v); np.save(sys.argv[2]+'_f.npy',f)
render.views_dir(v,n,sys.argv[2]+'.png',[([0,0,-1],[0,1,0]),([0,0,1],[0,1,0]),([0,1,0],[0,0,1]),([0,-1,0],[0,0,1]),([1,0,0],[0,0,1]),([-1,0,0],[0,0,1])],res=float(sys.argv[4]) if len(sys.argv)>4 else 0.9)
