#include <comp.hpp>
#include <python_ngstd.hpp>

namespace ngfem
{
  class ComposeCoefficientFunction : public CoefficientFunction
  {
    shared_ptr<CoefficientFunction> c1;
    shared_ptr<CoefficientFunction> c2;
    shared_ptr<ngcomp::MeshAccess> ma;

  public:
    ComposeCoefficientFunction (shared_ptr<CoefficientFunction> ac1,
                              shared_ptr<CoefficientFunction> ac2,
                                shared_ptr<ngcomp::MeshAccess> ama);
    ///
    virtual double Evaluate (const BaseMappedIntegrationPoint & ip) const;
    virtual double EvaluateConst () const;
    virtual void Evaluate (const BaseMappedIntegrationPoint & ip, FlatVector<> result) const;
    virtual void TraverseTree (const function<void(CoefficientFunction&)> & func);
    virtual void PrintReport (ostream & ost) const;
  };
}
