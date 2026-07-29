# Data Dictionary

All CSV files in this directory are the only data files in the repository.
No code lives here. Paths are relative to `data/`.

Robot platform: Svaya Robotics 6-DoF collaborative arm, harmonic drives,
gear ratio N = 100, logged at 200 Hz via Svaya API v2.1.1 on 12 June 2026.
Joints studied: 1, 2, 3, 5 (J4 and J6 excluded).

---

## raw/

Raw API log files, one per joint. Unmodified from the robot.

| File | Joint | Rows (approx) |
|------|-------|---------------|
| `joint1_raw.csv` | J1 | ~47 000 |
| `joint2_raw.csv` | J2 | ~4 100 |
| `joint3_raw.csv` | J3 | ~11 600 |
| `joint5_raw.csv` | J5 | ~32 000 |

Columns (all joints share the same schema):

| Column | Unit | Description |
|--------|------|-------------|
| `timestamp` | HH:MM:SS.fff | Wall-clock time of sample |
| `m_t_{j}` | N·mm | Motor torque (motor side) |
| `jts{j}` | N·mm | Joint torque sensor reading (joint side; sign convention: sensor reads negative of reaction torque) |
| `v{j}` | deg/s | Joint velocity from API |
| `q{j}` | deg | Joint position |
| *(other columns)* | — | Additional API fields; not used in modelling |

Friction torque label used throughout: `Tf = N × m_t_{j} − (−jts{j}) = N × m_t_{j} + jts{j}`

---

## interim/

Per-joint CSVs with only the five relevant columns selected from raw.
Produced by `pipeline/cleaning.py`.

| File | Description |
|------|-------------|
| `joint{n}_clean.csv` | `timestamp, m_t_{n}, jts{n}, v{n}, q{n}` |

---

## processed/

Cleaned data with computed kinematic derivatives.
Produced by `pipeline/velocity.py` and `pipeline/acceleration.py`.

| File | Added column | Formula |
|------|-------------|---------|
| `joint{n}_velocity.csv` | `velocity` (rad/s), `time_seconds` (s) | `dq/dt` via finite difference |
| `joint{n}_acceleration.csv` | `acceleration` (rad/s²), `time_seconds` (s) | `dv/dt` via finite difference |

---

## deduplicated/

Deduplicated versions of the processed files (duplicate timestamps removed).
Used in some exploratory analyses.

| File | Description |
|------|-------------|
| `joint{n}_velocity_unique.csv` | Unique-timestamp velocity data |
| `joint{n}_acceleration_unique.csv` | Unique-timestamp acceleration data |

---

## gravity_tests/

Separate experiments to characterise gravity torque at specific configurations.

| File | Description |
|------|-------------|
| `gravity_enabled_90deg.csv` | Arm held at 90° with gravity compensation enabled |
| `position_sweep_0_to_90deg.csv` | Slow sweep from 0° to 90° to measure real gravity torque profile |
