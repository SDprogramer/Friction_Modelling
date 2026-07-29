"""Smoke tests that run without the ML dependencies or the dataset."""
import numpy as np

from friction_modelling.config import JOINTS, N_GEAR, REF_PARAMS
from friction_modelling.models import physics_model as pm


def test_constants():
    assert N_GEAR == 100
    assert set(JOINTS) == {1, 2, 3, 5}
    assert set(REF_PARAMS) == set(JOINTS)


def test_friction_model_shape_and_values():
    # τ_f = Tc·tanh(v_eff/Vs) + Bv·v_eff + C0 ; with zero params -> zeros.
    X = np.array([[0.0, 0.0], [1.0, 0.5], [-2.0, 1.0]])
    ps = np.array([1.0, 1.0, 1.0, 0.0, 0.0])
    sc = np.array([0.0, 0.0, 1.0, 1.0, 0.0])  # Tc=0, Bv=0 -> output all zeros
    out = pm._friction(ps, sc, X)
    assert out.shape == (3,)
    assert np.allclose(out, 0.0)


def test_friction_pure_viscous():
    # Only viscous term active: τ_f = Bv * v (Cp=0).
    X = np.array([[2.0, 0.0], [-3.0, 0.0]])
    ps = np.array([0.0, 1.0, 1.0, 0.0, 0.0])
    sc = np.array([1.0, 4.0, 1.0, 1.0, 1.0])  # Bv = 4
    out = pm._friction(ps, sc, X)
    assert np.allclose(out, [8.0, -12.0])
