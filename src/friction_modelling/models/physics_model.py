"""Modified Coulomb-Viscous analytical friction model.

τ_f = Tc·tanh(v_eff / Vs) + Bv·v_eff + C0
v_eff = v + Cp·q

Parameters identified per joint via scipy TRF with Huber (soft_l1) loss.
"""
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

from friction_modelling.config import JOINTS, OUTPUT_ROOT, PATHS, RANDOM_STATE, ensure_output_dirs
from friction_modelling.pipeline.loader import load_joint

warnings.filterwarnings("ignore")


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #
def _friction(ps: np.ndarray, sc: np.ndarray, X: np.ndarray) -> np.ndarray:
    Tc = ps[0] * sc[0]
    Bv = ps[1] * sc[1]
    Vs = ps[2] * sc[2]
    Cp = ps[3] * sc[3]
    C0 = ps[4] * sc[4]
    v, q = X[:, 0], X[:, 1]
    v_eff = v + Cp * q
    return Tc * np.tanh(v_eff / Vs) + Bv * v_eff + C0


def _fit(X_train: np.ndarray, y_train: np.ndarray):
    Tc_init = float(np.percentile(np.abs(y_train), 85))
    C0_init = float(np.mean(y_train))
    C0_sc = max(abs(C0_init), 0.01)
    scale = np.array([Tc_init, 50.0, 0.05, 1.0, C0_sc])
    p0 = np.array([1.0, 0.5, 1.0, 0.0, float(np.sign(C0_init)) if C0_init != 0 else 0.0])
    lb = [1e-6 / scale[0], 1e-6 / scale[1], 1e-6 / scale[2], -np.inf, -np.inf]
    result = least_squares(
        lambda ps, sc, X, y: _friction(ps, sc, X) - y,
        p0,
        args=(scale, X_train, y_train),
        bounds=(lb, [np.inf] * 5),
        method="trf",
        loss="soft_l1",
        f_scale=1.0,
        max_nfev=8000,
        ftol=1e-12, xtol=1e-12, gtol=1e-12,
        verbose=0,
    )
    return result, scale


def _metrics(y_true, y_pred):
    mse = mean_squared_error(y_true, y_pred)
    return mse, float(np.sqrt(mse)), float(mean_absolute_error(y_true, y_pred))


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def run(paths=PATHS) -> pd.DataFrame:
    """Fit the physics model for all joints; return a metrics DataFrame."""
    ensure_output_dirs()
    rows = []

    for j in JOINTS:
        X, y, _ = load_joint(j, paths)
        X_tr, X_tmp, y_tr, y_tmp = train_test_split(
            X, y, test_size=0.30, random_state=RANDOM_STATE, shuffle=True
        )
        X_val, X_te, y_val, y_te = train_test_split(
            X_tmp, y_tmp, test_size=2 / 3, random_state=RANDOM_STATE, shuffle=True
        )

        result, scale = _fit(X_tr, y_tr)
        Tc, Bv, Vs, Cp, C0 = [result.x[i] * scale[i] for i in range(5)]

        _, rmse_v, mae_v = _metrics(y_val, _friction(result.x, scale, X_val))
        _, rmse_t, mae_t = _metrics(y_te, _friction(result.x, scale, X_te))

        print(
            f"J{j}  Tc={Tc:.4f}  Bv={Bv:.4f}  Vs={Vs:.6f}  Cp={Cp:.4f}  C0={C0:.4f}"
            f"  | test RMSE={rmse_t:.4f}  MAE={mae_t:.4f}"
        )
        rows.append(
            dict(
                Joint=f"J{j}",
                Tc_Nmm=round(Tc, 6),
                Bv_NmmSR=round(Bv, 6),
                Vs_radS=round(Vs, 8),
                Cp=round(Cp, 6),
                C0_Nmm=round(C0, 6),
                Val_RMSE=round(rmse_v, 5),
                Val_MAE=round(mae_v, 5),
                Test_RMSE=round(rmse_t, 5),
                Test_MAE=round(mae_t, 5),
            )
        )

    df = pd.DataFrame(rows).set_index("Joint")
    out = OUTPUT_ROOT / "params" / "physics_model_params.csv"
    df.to_csv(out)
    print(f"\nSaved parameters -> {out}")
    return df


if __name__ == "__main__":
    run()
