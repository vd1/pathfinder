import numpy as np
from scipy.linalg import eigh
def J40(N,h=1.0,a=1.0):
    J=np.zeros((2*N,2*N))
    for n in range(N):
        J[n,n]=-h
        for m in range(N):
            J[n,N+m]= a/(N-1) if m==n else -a*N/(N-1)**2
            J[N+n,m]= a/(N-1)
            J[N+n,N+m]= -a if m==n else a/(N-1)
    return J
for N in [3,10,50,200]:
    J=J40(N); best=(-1e9,None,None)
    for e in np.linspace(-0.95,0.95,77):
        for w in np.linspace(0.05,4,80):
            if w-e*e<=1e-6: continue
            P=np.kron(np.array([[1,e],[e,w]]),np.eye(N))
            S=-(P@J+J.T@P)/2
            mI=np.linalg.eigvalsh(S).min()
            mP=eigh(S,P,eigvals_only=True).min()
            if mP>best[0]: best=(mP,mI,(e,w))
    print(N,"best modulus rel P %.4f  rel I %.4f  at e,w=%s"%best)
