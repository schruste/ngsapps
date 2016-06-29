# http://www.math.umn.edu/~scheel/preprints/pf0.pdf

import numpy as np
import numpy.random as random
import scipy.sparse as sp
import scipy.sparse.linalg as splinalg
import multiprocessing as mp

from netgen.geom2d import unit_square, MakeCircle, SplineGeometry
from netgen.meshing import Element0D, Element1D, Element2D, MeshPoint, \
                                       FaceDescriptor, Mesh as NetMesh
from netgen.csg import Pnt
from ngsolve import *

np.set_printoptions(linewidth=400, threshold=100000)

# L = 10
# N = 4
# L = 700
L = 200
# N = 70
N = 40
dx = L / N

# dt = 0.05
dt = 0.2
# tend = -1
tend = 400

gamma = 0.1
alpha = 0.2
kappa = 0

delta = 0.1

continuous_ngplot = True

# load initial conditions from file (see precip_draw_ic.py)
icfile = None
# icfile = open('precip.ic', 'rb')

outfile = None
# outfile = open('precip2d.bin', 'wb')

rowidxs = []
colidxs = []
data = []

def to_vec_index(func, coord):
    # c00, c10, c20, ... , cN0 , c01, ... , cNN, e00, ...
    i, j = coord
    if func == 'c':
        return i + j * (N + 1)
    elif func == 'e':
        return (N + 1) ** 2 + i + j * (N + 1)

def newentry(i, j, d):
    # B[i, j] = d
    rowidxs.append(i)
    colidxs.append(j)
    data.append(d)

def add_laplace(func, scale, a, b, c):
    newentry(to_vec_index(func, b), to_vec_index(func, a), scale / dx ** 2)
    newentry(to_vec_index(func, b), to_vec_index(func, b), -2 * scale / dx ** 2)
    newentry(to_vec_index(func, b), to_vec_index(func, c), scale / dx ** 2)

for i in range(N + 1):
    for j in range(N + 1):
        if i > 0 and i < N:
            add_laplace('c', 1, (i-1,j), (i,j), (i+1,j))
            add_laplace('e', kappa, (i-1,j), (i,j), (i+1,j))
        if j > 0 and j < N:
            add_laplace('c', 1, (i,j-1), (i,j), (i,j+1))
            add_laplace('e', kappa, (i,j-1), (i,j), (i,j+1))

        newentry(to_vec_index('c', (i,j)), to_vec_index('c', (i,j)), -gamma)
        newentry(to_vec_index('e', (i,j)), to_vec_index('c', (i,j)), gamma)

def add_neumann(func, scale, bnd, inner):
    newentry(to_vec_index(func, bnd), to_vec_index(func, bnd), -scale / dx ** 2)
    newentry(to_vec_index(func, bnd), to_vec_index(func, inner), scale / dx ** 2)

for i in range(N + 1):
    for f, s in [('c', 1), ('e', kappa)]:
        add_neumann(f, s, (i,0), (i,1))
        add_neumann(f, s, (i,N), (i,N-1))
        add_neumann(f, s, (0,i), (1,i))
        add_neumann(f, s, (N,i), (N-1,i))

B = sp.coo_matrix((data, (rowidxs, colidxs)),
                  shape=(2 * (N + 1) ** 2, 2 * (N + 1) ** 2))
B *= -dt
B += sp.eye(2 * (N + 1) ** 2)
B = B.tocsr()
# print(B.todense())


def AApply(u):
    v = u[(N + 1) ** 2:]
    w = v * (1 - v) * (v - alpha)
    # print(dt * np.hstack((w, -w)))
    return dt * np.hstack((w, -w))

def AssembleLinearization(u):
    rightm = sp.dia_matrix((-3 * u[(N + 1) ** 2:] ** 2
                            + 2 * (1 + alpha) * u[(N + 1) ** 2:]
                            - alpha, 0), ((N + 1) ** 2, (N + 1) ** 2))
    Alin = sp.bmat([[sp.coo_matrix(((N + 1) ** 2, (N + 1) ** 2)), rightm],
                    [None, -rightm]])
    # print(dt * Alin.toarray())
    return dt * Alin


netmesh = NetMesh()
netmesh.dim = 2

if continuous_ngplot:
    M = N
else:
    M = N+1

pnums = []
for i in range(M + 1):
    for j in range(M + 1):
        pnums.append(netmesh.Add(MeshPoint(Pnt(L * i / M, L * j / M, 0))))

netmesh.Add (FaceDescriptor(surfnr=1,domin=1,bc=1))
netmesh.SetMaterial(1, 'mat')
for j in range(M):
    for i in range(M):
        netmesh.Add(Element2D(1, [pnums[i + j * (M + 1)],
                                  pnums[i + (j + 1) * (M + 1)],
                                  pnums[i + 1 + (j + 1) * (M + 1)],
                                  pnums[i + 1 + j * (M + 1)]]))

    netmesh.Add(Element1D([pnums[M + j * (M + 1)],
                           pnums[M + (j + 1) * (M + 1)]], index=1))
    netmesh.Add(Element1D([pnums[0 + j * (M + 1)],
                           pnums[0 + (j + 1) * (M + 1)]], index=1))

for i in range(M):
    netmesh.Add(Element1D([pnums[i], pnums[i + 1]], index=1))
    netmesh.Add(Element1D([pnums[i + M * (M + 1)],
                           pnums[i + 1 + M * (M + 1)]], index=1))

mesh = Mesh(netmesh)
if continuous_ngplot:
    Vvis = H1(mesh, order=1)
else:
    Vvis = L2(mesh, order=0)
fes = FESpace([Vvis, Vvis])
svis = GridFunction(fes)

s = np.zeros(2 * (N + 1) ** 2)
if icfile:
    s += np.load(icfile)
    icfile.close()
    svis.vec.FV().NumPy()[:] = s
else:
    # s = random.rand(2 * (N + 1) ** 2)
    # s = np.hstack((np.full(2 * (N + 1), delta),
    #                 np.full(2 * (N + 1), -delta),
    #                 np.zeros((N + 1) ** 2 - 4 * (N + 1)),
    #                 np.full((N + 1) ** 2, alpha)))
    # s = np.hstack((np.full(10 * (N + 1), delta),
    #                 np.full(10 * (N + 1), -delta),
    #                 np.zeros((N + 1) ** 2 - 20 * (N + 1)),
    #                 np.full((N + 1) ** 2, alpha)))
    # svis.vec.FV().NumPy()[:] = s
    width = 200
    svis.components[0].Set(exp(-((x-L/2) * (x-L/2) + (y-L/2) * (y-L/2))/ width))
    svis.components[1].Set(CoefficientFunction(alpha))
    s = svis.vec.FV().NumPy()

Draw(svis.components[0], mesh, 'c')
Draw(svis.components[1], mesh, 'e')

def plot_proc(sinit, t_sh, s_sh):
    import matplotlib.pyplot as plt
    ts = [0]
    masses = [sinit.sum()]
    fig_mass = plt.figure()
    ax_mass = fig_mass.add_subplot(111)
    line_mass, = ax_mass.plot(ts, masses, "g", label=r"$\int\;c + e$")
    ax_mass.legend()

    plt.show(block=False)
    while True:
        with t_sh.get_lock(), s_sh.get_lock():
            t = t_sh.value
            s = np.array(s_sh[:])
        if t == -1:
            break
        elif t != ts[-1]:
            ts.append(t)
            masses.append(s.sum())
            line_mass.set_xdata(ts)
            line_mass.set_ydata(masses)
            ax_mass.relim()
            ax_mass.autoscale_view()

        plt.pause(0.05)

    plt.show()

t_sh = mp.Value('d', 0.0)
s_sh = mp.Array('d', s)
proc = mp.Process(target=plot_proc, args=(s, t_sh, s_sh))
proc.start()

input('Press any key...\n\n')
if outfile:
    np.save(outfile, L)
    np.save(outfile, dt)
    np.save(outfile, s)

# implicit Euler
t = 0.0
while tend < 0 or t < tend - dt / 2:
    print('\n\nt = {:10.2f}'.format(t))

    sold = np.copy(s)
    wnorm = 1e99

    # Newton solver
    while wnorm > 1e-9:
        rhs = np.copy(sold)
        rhs -= B.dot(s)
        As = AApply(s)
        rhs -= As
        Alin = AssembleLinearization(s)

        w = splinalg.spsolve(B + Alin, rhs)
        wnorm = np.linalg.norm(w)
        print('|w| = {:7.3e} '.format(wnorm),end='')
        s += w
        # input('')

    t += dt
    with t_sh.get_lock(), s_sh.get_lock():
        t_sh.value = t
        s_sh[:] = s
    svis.vec.FV().NumPy()[:] = s
    Redraw(blocking=False)
    if outfile:
        np.save(outfile, s)

print('\n\nt = {:10.2f}'.format(t))
if outfile:
    outfile.close()
t_sh.value = -1
