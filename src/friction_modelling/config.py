"""Central configuration: paths, robot constants, model hyper-parameters.

All filesystem paths derive from DATA_ROOT so the code runs unchanged on a
developer laptop or inside a Docker container. Set the FRICTION_DATA_ROOT
environment variable to override; otherwise defaults to data/ at the repo root.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Robot / experiment constants
# --------------------------------------------------------------------------- #
N_GEAR: int = 100          # harmonic-drive gear ratio (motor -> joint)
FS_HZ: int = 200           # data logging frequency
DT: float = 1.0 / FS_HZ    # sample period (s)

JOINTS: tuple[int, ...] = (1, 2, 3, 5)  # J4, J6 excluded

RANDOM_STATE: int = 42

# Raw API log file names inside data/raw/
RAW_FILES: dict[int, str] = {
    1: "joint1_raw.csv",
    2: "joint2_raw.csv",
    3: "joint3_raw.csv",
    5: "joint5_raw.csv",
}


def _default_data_root() -> Path:
    """Repo-relative data/ directory, overridable via FRICTION_DATA_ROOT."""
    env = os.environ.get("FRICTION_DATA_ROOT")
    if env:
        return Path(env)
    # src/friction_modelling/config.py -> repo root is 3 parents up
    return Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class Paths:
    """Resolved directory layout."""

    data_root: Path = field(default_factory=_default_data_root)

    @property
    def raw(self) -> Path:
        return self.data_root / "raw"

    @property
    def interim(self) -> Path:
        return self.data_root / "interim"

    @property
    def processed(self) -> Path:
        return self.data_root / "processed"

    def raw_file(self, joint: int) -> Path:
        return self.raw / RAW_FILES[joint]

    def interim_file(self, joint: int) -> Path:
        return self.interim / f"joint{joint}_clean.csv"

    def vel_file(self, joint: int) -> Path:
        return self.processed / f"joint{joint}_velocity.csv"

    def acc_file(self, joint: int) -> Path:
        return self.processed / f"joint{joint}_acceleration.csv"


# Output directory for generated artefacts (params CSVs, figures, models).
def _default_output_root() -> Path:
    env = os.environ.get("FRICTION_OUTPUT_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "outputs"


PATHS = Paths()
OUTPUT_ROOT = _default_output_root()


# --------------------------------------------------------------------------- #
# Model hyper-parameters
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class NNConfig:
    hidden_units: tuple[int, ...] = (64, 64, 32)
    activation: str = "tanh"
    optimizer: str = "adam"
    batch_size: int = 512
    max_epochs: int = 1000
    patience: int = 20


@dataclass(frozen=True)
class PINNConfig:
    train_frac: float = 0.70
    val_frac: float = 0.15         # remaining 15% -> test
    epochs: int = 2000
    batch_size: int = 512
    lr: float = 1e-3
    patience: int = 80
    ref_weight: float = 0.3        # weight of reference (Coulomb-Viscous) loss


NN_CONFIG = NNConfig()
PINN_CONFIG = PINNConfig()

# Reference Coulomb-Viscous parameters (identified by the physics model);
# used to anchor the PINN. Kept here so all modules share one source of truth.
REF_PARAMS: dict[int, dict[str, float]] = {
    1: dict(Tc=10.552847, Bv=15.756983, Vs=0.005887, Cp=0.001307, C0_ref=0.912754),
    2: dict(Tc=1.505837, Bv=33.409906, Vs=0.017231, Cp=0.548419, C0_ref=-0.378301),
    3: dict(Tc=0.264921, Bv=15.424438, Vs=0.000983, Cp=0.345742, C0_ref=-0.430260),
    5: dict(Tc=3.164319, Bv=1.389227, Vs=0.004955, Cp=0.003987, C0_ref=-0.100190),
}


def ensure_output_dirs() -> None:
    """Create the output tree if it does not exist."""
    for sub in ("params", "figures", "models"):
        (OUTPUT_ROOT / sub).mkdir(parents=True, exist_ok=True)
