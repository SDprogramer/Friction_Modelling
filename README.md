# Robotic Arm Joint Friction Modelling

Estimation of joint friction in a **6-DoF Svaya Robotics collaborative arm**
(harmonic-drive transmissions, gear ratio `N = 100`), developed at
**CSIR-CMERI, Durgapur**.

Three friction-modelling approaches are implemented as an installable Python
package and driven through an interactive **website** (FastAPI + a single-page
frontend) served on **localhost**:

| Model | Module | What it does |
|-------|--------|--------------|
| Modified Coulomb-Viscous | `src/friction_modelling/models/physics_model.py` | Analytical fit (`scipy` TRF, Huber loss) |
| Black-box Neural Net | `src/friction_modelling/models/neural_net.py` | MLP `[q,v] → Tf`, cycle-aware split |
| PINN (LuGre) | `src/friction_modelling/models/pinn.py` | Physics-informed LuGre parameter identification |

## Quick start (Windows, no Docker)

```bat
setup.bat          REM one-time: creates .venv on Python 3.13, installs deps
run_website.bat    REM FastAPI + JS site      -> http://localhost:8501
run_dashboard.bat  REM Streamlit dashboard    -> http://localhost:8502
run_pipeline.bat   REM CLI: preprocess + all 3 models, no server needed
```

`setup.bat` pins the virtual environment to **Python 3.13** even if your
system default is 3.14, because TensorFlow (needed for the neural-net and
PINN models) does not publish 3.14 wheels yet. Your system Python 3.14
install is untouched; 3.13 only lives inside this project's `.venv`. See
`setup.bat` if 3.13 isn't installed yet - it will point you to the installer.

The `webapp/static` frontend is plain HTML/CSS/JS served directly by
FastAPI - no Node.js/npm required to run it.

## Project layout

```
Friction_Modelling/
├── Dockerfile                  # container image (python:3.11-slim)
├── docker-compose.yml          # localhost service on :8501, mounts ./data
├── Makefile                    # convenience targets
├── pyproject.toml              # installable package `friction-modelling`
├── requirements.txt
├── .streamlit/config.toml
│
├── data/                       # DATA ONLY — CSV files, no code
│   ├── raw/                    # joint{1,2,3,5}_raw.csv        (raw API logs)
│   ├── interim/                # joint{n}_clean.csv            (columns selected)
│   ├── processed/              # joint{n}_velocity.csv, joint{n}_acceleration.csv
│   ├── deduplicated/           # joint{n}_*_unique.csv
│   ├── gravity_tests/          # gravity_enabled_90deg.csv, position_sweep_0_to_90deg.csv
│   └── README.md               # data dictionary
│
├── src/friction_modelling/     # the .py package
│   ├── config.py               # paths, constants, hyper-parameters
│   ├── cli.py                  # python -m friction_modelling.cli <stage>
│   ├── pipeline/               # cleaning → velocity → acceleration → loader
│   ├── models/                 # physics_model, neural_net, pinn
│   ├── viz/plots.py            # figure builders for the site / dashboard
│   └── webapp/                 # FastAPI backend + static single-page frontend
│       ├── api.py              # JSON API + serves the site
│       ├── __main__.py         # `friction-web` launcher (uvicorn)
│       └── static/             # index.html, style.css, app.js
│
├── dashboard/streamlit_app.py  # legacy Streamlit dashboard (optional)
├── scripts/collect_data.py     # robot-side data-acquisition (Svaya API)
├── notebooks/                  # original research notebooks (01→07)
├── tests/                      # pytest smoke tests
├── outputs/                    # generated params / figures / models (git-ignored)
└── docs/                       # reports, presentations, figures, references, robot manuals
```

Experiment data lives in `data/` and is **mounted** into the container — never
copied into the image.

## Run on localhost with Docker

From the repository root:

```bash
docker compose up --build
```

Then open **http://localhost:8501** — the friction-modelling website. From the
browser you can inspect data readiness per joint, view diagnostic plots, run the
preprocessing pipeline, train each model as a background job, and read back the
identified parameters.

The compose file mounts `./data` at `/data` (read-only) and persists results to
`./outputs`. To point at a different dataset, set `FRICTION_DATA_ROOT`.

Stop with `Ctrl+C`, or `docker compose down`.

## Run without Docker (local Python)

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
pip install -e .

# Full preprocessing + all three models from the command line:
python -m friction_modelling.cli all

# Launch the website (FastAPI) directly:
friction-web                         # http://localhost:8501
# equivalently:
python -m friction_modelling.webapp --port 8501 --reload

# Or the legacy Streamlit dashboard:
streamlit run dashboard/streamlit_app.py
```

## CLI stages

```bash
python -m friction_modelling.cli clean         # raw logs → per-joint CSVs
python -m friction_modelling.cli velocity      # add dq/dt
python -m friction_modelling.cli acceleration  # add dv/dt
python -m friction_modelling.cli preprocess    # the three steps above
python -m friction_modelling.cli physics       # fit Coulomb-Viscous
python -m friction_modelling.cli nn            # train MLP
python -m friction_modelling.cli pinn          # train LuGre PINN
python -m friction_modelling.cli all           # everything
```

## Tests

```bash
pip install pytest
pytest
```

## Friction label convention

Throughout, friction torque is `Tf = N·Tm + Tj` with gear ratio `N = 100`,
where `Tm` is motor torque and `Tj` the joint-side torque sensor reading (its
sign convention produces the `−(−Tj)` in code). Joints J4 and J6 are excluded.

## Documentation

Reports, slides, result figures, reference papers, and robot manuals are under
[`docs/`](docs/) (kept on disk, excluded from git to avoid committing large
binaries).
