import numpy as np, networkx as nx
from skimage.morphology import skeletonize
F=np.load('sdf_s.npy',mmap_mode='r'); g=np.load('grid.npy'); lo=g[:3]; h=g[3]
s=3
E=np.asarray(F[::s,::s,::s])<0
sk=skeletonize(E)
pts=np.argwhere(sk)
print('skel pts',len(pts))
X=pts*h*s+lo+h/2
# graph
idx={tuple(p):i for i,p in enumerate(pts)}
G=nx.Graph()
for i,p in enumerate(pts):
    for d in np.array(np.meshgrid([-1,0,1],[-1,0,1],[-1,0,1])).reshape(3,-1).T:
        if not d.any(): continue
        j=idx.get(tuple(p+d))
        if j is not None: G.add_edge(i,j,weight=np.linalg.norm(d))
# outlet point: max x ; take farthest pair via double BFS from it
G=G.subgraph(max(nx.connected_components(G),key=len))
nodes=list(G.nodes)
start=max(nodes,key=lambda i:X[i,0])
d1=nx.single_source_dijkstra_path_length(G,start)
far=max(d1,key=d1.get)
path=nx.dijkstra_path(G,start,far)
C=X[path]
np.save('centerline_raw.npy',C)
print('path len',len(C),'start',C[0].round(1),'end',C[-1].round(1))
