"""Streamlit dashboard — the localhost app served by Docker.

Run locally:   streamlit run dashboard/streamlit_app.py
Run in Docker: docker compose up   ->   http://localhost:8501
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the src package importable when run directly by Streamlit.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import streamlit as st

from friction_modelling import __version__
from friction_modelling.config import JOINTS, OUTPUT_ROOT, PATHS
from friction_modelling.viz.plots import friction_vs_velocity_figure, raw_signals_figure

st.set_page_config(page_title="Robotic Arm Friction Modelling", layout="wide")

st.title("🤖 Joint Friction Modelling — 6-DoF Robotic Arm")
st.caption(f"CSIR-CMERI · Svaya Robotics · v{__version__}")

data_ok = any(PATHS.raw_file(j).exists() for j in JOINTS)
if not data_ok:
    st.error(f"Experiment data not found at `{PATHS.data_root}`. "
             "Mount the data directory or set FRICTION_DATA_ROOT.")

# --------------------------------------------------------------------------- #
# Sidebar controls
# --------------------------------------------------------------------------- #
st.sidebar.header("Controls")
joint = st.sidebar.selectbox("Joint", JOINTS, index=0)
st.sidebar.markdown("---")
st.sidebar.subheader("Run models")
run_physics = st.sidebar.button("Fit Physics model")
run_nn = st.sidebar.button("Train Neural Net")
run_pinn = st.sidebar.button("Train PINN")

# --------------------------------------------------------------------------- #
# Data exploration
# --------------------------------------------------------------------------- #
tab_data, tab_physics, tab_nn, tab_pinn = st.tabs(
    ["📈 Data", "🧮 Physics model", "🧠 Neural Net", "⚗️ PINN (LuGre)"]
)

with tab_data:
    if data_ok:
        st.subheader(f"Joint {joint} — raw signals")
        st.pyplot(raw_signals_figure(joint))
        st.subheader(f"Joint {joint} — friction torque vs velocity")
        st.pyplot(friction_vs_velocity_figure(joint))


def _show_csv(path: Path, empty_msg: str):
    if path.exists():
        st.dataframe(pd.read_csv(path))
    else:
        st.info(empty_msg)


with tab_physics:
    st.markdown(
        r"$\tau_f = T_c\tanh(v_{eff}/V_s) + B_v\,v_{eff} + C_0,\quad v_{eff}=v+C_p q$"
    )
    if run_physics:
        with st.spinner("Fitting Coulomb-Viscous model for all joints..."):
            from friction_modelling.models.physics_model import run
            st.dataframe(run())
    else:
        _show_csv(OUTPUT_ROOT / "params" / "physics_model_params.csv",
                  "Press **Fit Physics model** in the sidebar.")

with tab_nn:
    st.markdown("MLP `[q, v] → Dense(64,64,32) → Tf`, cycle-aware split.")
    if run_nn:
        with st.spinner("Training neural network (this can take a minute)..."):
            from friction_modelling.models.neural_net import run
            st.dataframe(run())
    else:
        _show_csv(OUTPUT_ROOT / "params" / "neural_net_metrics.csv",
                  "Press **Train Neural Net** in the sidebar.")

with tab_pinn:
    st.markdown("Physics-informed net identifying LuGre parameters "
                r"$(\sigma_0,\sigma_1,\sigma_2,F_c,F_s,v_s)$.")
    if run_pinn:
        with st.spinner("Training PINN (this can take a few minutes)..."):
            from friction_modelling.models.pinn import run
            st.dataframe(run())
    else:
        _show_csv(OUTPUT_ROOT / "params" / "pinn_lugre_params.csv",
                  "Press **Train PINN** in the sidebar.")
