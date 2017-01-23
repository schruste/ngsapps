from libngsapps_utils import *

from ngsolve import *
from netgen.meshing import Element0D, Element1D, Element2D, MeshPoint, \
                                       FaceDescriptor, Mesh as NetMesh
from netgen.csg import Pnt

def Lagrange(mesh, **args):
    """
    Create H1 finite element space with Lagrange basis.
    documentation of arguments is available in FESpace.
    """
    fes = FESpace("lagrangefespace", mesh, **args)
    return fes

def GenerateGridMesh(p1, p2, N, M, bc=1, bcs=None):
    """
    Generate a rectangular grid mesh spanned by points p1, p2
    with N elements in x direction, M elements in y direction.
    The return type is a netgen mesh.
    """
    p1x, p1y = p1
    p2x, p2y = p2
    p1x,p2x = min(p1x,p2x), max(p1x, p2x)
    p1y,p2y = min(p1y,p2y), max(p1y, p2y)
    if not bcs: bcs=4*[bc]

    netmesh = NetMesh()
    netmesh.dim = 2

    pnums = []
    for j in range(M + 1):
        for i in range(N + 1):
            pnums.append(netmesh.Add(MeshPoint(Pnt(p1x + (p2x-p1x) * i / N,
                                                   p1y + (p2y-p1y) * j / M, 0))))

    for bc in bcs:
        netmesh.Add(FaceDescriptor(bc=bc))
    for j in range(M):
        for i in range(N):
            netmesh.Add(Element2D(1, [pnums[i + j * (N + 1)],
                                     pnums[i + (j + 1) * (N + 1)],
                                     pnums[i + 1 + (j + 1) * (N + 1)],
                                     pnums[i + 1 + j * (N + 1)]]))

        netmesh.Add(Element1D([pnums[N + j * (N + 1)],
                               pnums[N + (j + 1) * (N + 1)]], index=2))
        netmesh.Add(Element1D([pnums[0 + j * (N + 1)],
                               pnums[0 + (j + 1) * (N + 1)]], index=4))

    for i in range(N):
        netmesh.Add(Element1D([pnums[i], pnums[i + 1]], index=1))
        netmesh.Add(Element1D([pnums[i + M * (N + 1)],
                               pnums[i + 1 + M * (N + 1)]], index=3))

    return netmesh

class ConvolutionCache:
    def __init__(self, conv):
        self.conv = conv
    def __enter__(self):
        self.conv.CacheCF()
    def __exit__(self, t, v, trace):
        self.conv.ClearCFCache()
