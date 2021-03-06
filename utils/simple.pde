geometry = square.in2d
mesh = square.vol

shared = libngsapps_utils


define coefficient lam
1,

define coefficient coef_source
1,


# create an instance of our new FESpace

#define fespace v -type=myfespace -secondorder -dirichlet=[2]
define fespace v -type=lagrangefespace -order=5


#define gridfunction u -fespace=v -nested
define gridfunction u -fespace=v

# use our new laplace integrator (and standard robin integrator)
#define bilinearform a -fespace=v -symmetric -printelmat -fespace=v
#mylaplace lam

#define linearform f -fespace=v
#mysource coef_source


#numproc bvp np1 -bilinearform=a -linearform=f -gridfunction=u  -maxsteps=1000 -solver=direct

#numproc visualization npvis -scalarfunction=u -subdivision=1 -nolineartexture

#numproc drawflux npflux -solution=u -bilinearform=a -label=flux

numproc shapetester nptest -gridfunction=u
