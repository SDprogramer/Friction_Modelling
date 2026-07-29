"""FastAPI backend for the friction-modelling web frontend.

Serves a single-page website (static/) and a small JSON API that lets the user
drive the whole project from a browser:

  * inspect data availability per joint
  * view diagnostic plots (raw signals, friction-vs-velocity) as PNGs
  * preview processed CSVs
  * run the preprocessing pipeline and train each model as background jobs
  * read back the identified parameters / metrics

Run locally:   uvicorn friction_modelling.webapp.api:app --port 8501
Run in Docker: docker compose up   ->   http://localhost:8501
"""
from __future__ import annotations

import io
import threading
import time
import traceback
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable

import matplotlib
matplotlib.use("Agg")  # headless backend for server-side figures
import matplotlib.pyplot as plt
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from friction_modelling import __version__
from friction_modelling.config import FS_HZ, JOINTS, N_GEAR, OUTPUT_ROOT, PATHS
from friction_modelling.viz.plots import friction_vs_velocity_figure, raw_signals_figure

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Robotic-Arm Friction Modelling", version=__version__)


# --------------------------------------------------------------------------- #
# Model / stage registry
# --------------------------------------------------------------------------- #
def _run_physics() -> pd.DataFrame:
    from friction_modelling.models.physics_model import run
    return run()


def _run_nn() -> pd.DataFrame:
    from friction_modelling.models.neural_net import run
    return run()


def _run_pinn() -> pd.DataFrame:
    from friction_modelling.models.pinn import run
    return run()


def _run_preprocess() -> pd.DataFrame:
    from friction_modelling.pipeline.cleaning import clean_all
    from friction_modelling.pipeline.velocity import compute_velocity
    from friction_modelling.pipeline.acceleration import compute_acceleration
    clean_all()
    compute_velocity()
    compute_acceleration()
    return pd.DataFrame([{"stage": "preprocess", "status": "done"}])


# key -> (label, callable, result params CSV)
MODELS: dict[str, dict] = {
    "preprocess": dict(
        label="Preprocess pipeline",
        fn=_run_preprocess,
        result=None,
    ),
    "physics": dict(
        label="Coulomb-Viscous (physics) model",
        fn=_run_physics,
        result=OUTPUT_ROOT / "params" / "physics_model_params.csv",
    ),
    "nn": dict(
        label="Black-box neural network",
        fn=_run_nn,
        result=OUTPUT_ROOT / "params" / "neural_net_metrics.csv",
    ),
    "pinn": dict(
        label="LuGre physics-informed NN",
        fn=_run_pinn,
        result=OUTPUT_ROOT / "params" / "pinn_lugre_params.csv",
    ),
}


# --------------------------------------------------------------------------- #
# In-process background job runner
# --------------------------------------------------------------------------- #
_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()
_job_counter = 0


def _new_job_id(model: str) -> str:
    global _job_counter
    with _JOBS_LOCK:
        _job_counter += 1
        return f"{model}-{_job_counter}"


def _worker(job_id: str, fn: Callable[[], pd.DataFrame]) -> None:
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            df = fn()
        with _JOBS_LOCK:
            _JOBS[job_id].update(
                status="done",
                finished=time.time(),
                log=buf.getvalue(),
                result=_df_to_payload(df),
            )
    except Exception as exc:  # noqa: BLE001 — surface any failure to the UI
        with _JOBS_LOCK:
            _JOBS[job_id].update(
                status="error",
                finished=time.time(),
                log=buf.getvalue(),
                error=f"{exc}\n\n{traceback.format_exc()}",
            )


def _df_to_payload(df: pd.DataFrame) -> dict:
    df = df.reset_index()
    return {"columns": list(df.columns), "rows": df.to_dict(orient="records")}


# --------------------------------------------------------------------------- #
# API — status & data
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/status")
def status() -> dict:
    joints = []
    for j in JOINTS:
        joints.append(
            {
                "joint": j,
                "raw": PATHS.raw_file(j).exists(),
                "clean": PATHS.interim_file(j).exists(),
                "velocity": PATHS.vel_file(j).exists(),
                "acceleration": PATHS.acc_file(j).exists(),
            }
        )
    results = {
        key: (m["result"].exists() if m["result"] else None)
        for key, m in MODELS.items()
    }
    return {
        "version": __version__,
        "gear_ratio": N_GEAR,
        "sample_rate_hz": FS_HZ,
        "data_root": str(PATHS.data_root),
        "output_root": str(OUTPUT_ROOT),
        "joints": joints,
        "results": results,
        "data_ready": all(PATHS.raw_file(j).exists() for j in JOINTS),
    }


def _figure_response(fig) -> StreamingResponse:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.get("/api/data/{joint}/raw-plot")
def raw_plot(joint: int):
    _require_joint(joint)
    if not PATHS.raw_file(joint).exists():
        raise HTTPException(404, f"No raw data for joint {joint}")
    return _figure_response(raw_signals_figure(joint))


@app.get("/api/data/{joint}/friction-plot")
def friction_plot(joint: int):
    _require_joint(joint)
    if not PATHS.raw_file(joint).exists():
        raise HTTPException(404, f"No raw data for joint {joint}")
    return _figure_response(friction_vs_velocity_figure(joint))


@app.get("/api/data/{joint}/table")
def data_table(joint: int, rows: int = 100):
    _require_joint(joint)
    path = PATHS.vel_file(joint)
    if not path.exists():
        path = PATHS.raw_file(joint)
    if not path.exists():
        raise HTTPException(404, f"No data for joint {joint}")
    df = pd.read_csv(path, nrows=max(1, min(rows, 1000)))
    df.columns = df.columns.str.strip()
    return {
        "source": path.name,
        "columns": list(df.columns),
        "rows": df.round(6).to_dict(orient="records"),
    }


# --------------------------------------------------------------------------- #
# API — results
# --------------------------------------------------------------------------- #
@app.get("/api/results/{model}")
def results(model: str):
    m = _require_model(model)
    path = m["result"]
    if path is None or not path.exists():
        raise HTTPException(404, f"No saved results for '{model}' yet. Run it first.")
    df = pd.read_csv(path)
    return {
        "model": model,
        "label": m["label"],
        "file": path.name,
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records"),
    }


# --------------------------------------------------------------------------- #
# API — run jobs
# --------------------------------------------------------------------------- #
@app.post("/api/run/{model}")
def run_model(model: str):
    m = _require_model(model)
    if not all(PATHS.raw_file(j).exists() for j in JOINTS):
        raise HTTPException(400, "Raw data missing — cannot run.")

    job_id = _new_job_id(model)
    with _JOBS_LOCK:
        _JOBS[job_id] = dict(
            id=job_id, model=model, label=m["label"],
            status="running", started=time.time(), finished=None,
            log="", result=None, error=None,
        )
    threading.Thread(target=_worker, args=(job_id, m["fn"]), daemon=True).start()
    return {"job_id": job_id, "model": model, "status": "running"}


@app.get("/api/job/{job_id}")
def job_status(job_id: str):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            raise HTTPException(404, f"Unknown job '{job_id}'")
        return dict(job)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _require_joint(joint: int) -> None:
    if joint not in JOINTS:
        raise HTTPException(404, f"Joint {joint} not modelled (available: {list(JOINTS)})")


def _require_model(model: str) -> dict:
    m = MODELS.get(model)
    if m is None:
        raise HTTPException(404, f"Unknown model '{model}' (available: {list(MODELS)})")
    return m


# --------------------------------------------------------------------------- #
# Static site (mounted last so /api/* takes precedence)
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico")
def favicon():
    return JSONResponse({}, status_code=204)


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
