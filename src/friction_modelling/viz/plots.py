"""Diagnostic plotting helpers (return matplotlib figures for the dashboard)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from friction_modelling.config import N_GEAR, PATHS, Paths


def raw_signals_figure(joint: int, paths: Paths = PATHS):
    """4-panel raw signal plot (torques, velocity, position vs time)."""
    df = pd.read_csv(paths.raw_file(joint))
    df.columns = df.columns.str.strip()
    t = np.arange(len(df))
    q = np.deg2rad(df[f"q{joint}"])
    v = np.deg2rad(df[f"v{joint}"])
    tm = df[f"m_t_{joint}"]
    tj = df[f"jts{joint}"]

    fig, ax = plt.subplots(4, 1, figsize=(12, 8), sharex=True)
    ax[0].plot(t, tm); ax[0].set_ylabel("Tm (N·mm)"); ax[0].set_title(f"Joint {joint} — Motor Torque")
    ax[1].plot(t, tj); ax[1].set_ylabel("Tj (N·mm)"); ax[1].set_title("Joint Torque")
    ax[2].plot(t, v); ax[2].set_ylabel("v (rad/s)"); ax[2].set_title("Velocity")
    ax[3].plot(t, q); ax[3].set_ylabel("q (rad)"); ax[3].set_title("Position")
    ax[3].set_xlabel("Sample")
    fig.tight_layout()
    return fig


def friction_vs_velocity_figure(joint: int, paths: Paths = PATHS):
    """Scatter of measured friction torque vs velocity."""
    df = pd.read_csv(paths.raw_file(joint))
    df.columns = df.columns.str.strip()
    v = np.deg2rad(df[f"v{joint}"])
    tf = N_GEAR * df[f"m_t_{joint}"] - (-df[f"jts{joint}"])

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(v, tf, s=3, alpha=0.2)
    ax.set_xlabel("Velocity (rad/s)")
    ax.set_ylabel("Tf = N·Tm + Tj (N·mm)")
    ax.set_title(f"Joint {joint} — Friction Torque vs Velocity")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig
