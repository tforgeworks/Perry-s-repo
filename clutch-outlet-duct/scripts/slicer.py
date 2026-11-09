import numpy as np
def slice_segs(V,F,o,n):
    n=np.asarray(n,float)/np.linalg.norm(n); d=(V-o)@n
    df=d[F]; s=np.sign(df)
    hit=(s.min(1)<0)&(s.max(1)>0)
    T=F[hit]; D=df[hit]; P=V[T]
    segs=[]
    for (i,j) in [(0,1),(1,2),(2,0)]:
        c=(D[:,i]*D[:,j])<0
        t=np.where(c, D[:,i]/(D[:,i]-D[:,j]+1e-30),np.nan)
        segs.append(P[:,i]+t[:,None]*(P[:,j]-P[:,i]))
    S=np.stack(segs,1) # k,3,3 with one nan row
    out=[]
    for k in range(len(S)):
        r=S[k][~np.isnan(S[k][:,0])]
        if len(r)==2: out.append(r)
    return np.array(out)
