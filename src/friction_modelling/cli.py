"""Command-line entry point for the friction-modelling pipeline.

Usage:
    python -m friction_modelling.cli clean
    python -m friction_modelling.cli velocity
    python -m friction_modelling.cli acceleration
    python -m friction_modelling.cli physics
    python -m friction_modelling.cli nn
    python -m friction_modelling.cli pinn
    python -m friction_modelling.cli all      # full preprocessing + all models
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Robotic-arm joint friction modelling")
    parser.add_argument(
        "stage",
        choices=["clean", "velocity", "acceleration", "preprocess",
                 "physics", "nn", "pinn", "all"],
        help="pipeline stage to execute",
    )
    args = parser.parse_args(argv)

    if args.stage in ("clean", "preprocess", "all"):
        from friction_modelling.pipeline.cleaning import clean_all
        clean_all()
    if args.stage in ("velocity", "preprocess", "all"):
        from friction_modelling.pipeline.velocity import compute_velocity
        compute_velocity()
    if args.stage in ("acceleration", "preprocess", "all"):
        from friction_modelling.pipeline.acceleration import compute_acceleration
        compute_acceleration()
    if args.stage in ("physics", "all"):
        from friction_modelling.models.physics_model import run as run_physics
        run_physics()
    if args.stage in ("nn", "all"):
        from friction_modelling.models.neural_net import run as run_nn
        run_nn()
    if args.stage in ("pinn", "all"):
        from friction_modelling.models.pinn import run as run_pinn
        run_pinn()
    return 0


if __name__ == "__main__":
    sys.exit(main())
