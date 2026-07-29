"""Shared data loader used by all three models."""
from __future__ import annotations

import numpy as np
import pandas as pd
from friction_modelling.config import N_GEAR, PATHS, Paths


def load_joint(joint: int, paths: Paths = PATHS) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Return X=[v_rad, q_rad], y=Tf_Nmm, and the full DataFrame."""
    df = pd.read_csv(paths.vel_file(joint))
    df.columns = df.columns.str.strip()
    v = np.deg2rad(df[f"v{joint}"].values)
    q = np.deg2rad(df[f"q{joint}"].values)
    tm = df[f"m_t_{joint}"].values
    tj = df[f"jts{joint}"].values
    tf = N_GEAR * tm - (-tj)
    mask = np.isfinite(v) & np.isfinite(q) & np.isfinite(tf)
    X = np.column_stack([v, q])[mask]
    y = tf[mask]
    return X, y, df[mask].reset_index(drop=True)
