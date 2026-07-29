"""Step 1 – clean raw API logs and split by joint."""
from __future__ import annotations

import os
import pandas as pd
from friction_modelling.config import JOINTS, PATHS, RAW_FILES


def clean_all(paths=PATHS) -> None:
    os.makedirs(paths.interim, exist_ok=True)
    for joint in JOINTS:
        df = pd.read_csv(paths.raw_file(joint))
        cols = ["timestamp", f"m_t_{joint}", f"jts{joint}", f"v{joint}", f"q{joint}"]
        df[cols].to_csv(paths.interim_file(joint), index=False)
        print(f"Saved Joint {joint} -> {paths.interim_file(joint)}")


if __name__ == "__main__":
    clean_all()
