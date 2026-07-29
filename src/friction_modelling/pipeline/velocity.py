"""Step 2 – compute velocity (dq/dt) from cleaned joint CSVs."""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
from friction_modelling.config import JOINTS, PATHS


def compute_velocity(paths=PATHS) -> None:
    os.makedirs(paths.processed, exist_ok=True)
    for joint in JOINTS:
        df = pd.read_csv(paths.interim_file(joint))
        df["time_obj"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S.%f")
        df["time_seconds"] = (df["time_obj"] - df["time_obj"].iloc[0]).dt.total_seconds()
        dt = df["time_seconds"].diff()
        dq = df[f"q{joint}"].diff()
        df["velocity"] = dq / dt
        df.drop(columns=["time_obj"]).to_csv(paths.vel_file(joint), index=False)
        print(f"Saved velocity Joint {joint} -> {paths.vel_file(joint)}")


if __name__ == "__main__":
    compute_velocity()
