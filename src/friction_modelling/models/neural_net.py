"""Black-box MLP friction model with cycle-aware velocity-generalisation split.

Inputs  : [q (rad), v (rad/s)]
Target   : Tf = N·Tm + Tj  (N·m)
Split    : cycles assigned to train/test by peak velocity so the test set
           contains velocity ranges unseen in training (honest generalisation).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from friction_modelling.config import DT, JOINTS, N_GEAR, NN_CONFIG, OUTPUT_ROOT, PATHS, ensure_output_dirs


def _lazy_tf():
    import tensorflow as tf  # imported lazily so the pipeline runs without TF
    from tensorflow.keras.callbacks import EarlyStopping
    from tensorflow.keras.layers import Dense
    from tensorflow.keras.models import Sequential

    tf.random.set_seed(42)
    return tf, Sequential, Dense, EarlyStopping


def _load(joint: int, paths=PATHS):
    df = pd.read_csv(paths.interim_file(joint))
    q = np.deg2rad(df[f"q{joint}"].values)
    v = np.deg2rad(df[f"v{joint}"].values)
    tm = df[f"m_t_{joint}"].values
    tj = df[f"jts{joint}"].values
    tf_label = N_GEAR * tm - (-tj)
    v_deg = df[f"v{joint}"].values
    return q, v, v_deg, tf_label


def _cycle_split(v_deg: np.ndarray, joint: int):
    """Assign velocity cycles to train/test based on peak velocity."""
    zc = np.where(np.diff(np.sign(v_deg)))[0]
    starts = np.insert(zc, 0, 0)
    ends = np.append(zc, len(v_deg) - 1)

    cycles = []
    for s, e in zip(starts, ends):
        if s >= e:
            continue
        peak = float(np.max(np.abs(v_deg[s:e])))
        if peak < 5.0:
            continue
        cycles.append((s, e, peak))

    train_idx, test_idx = [], []
    if joint == 2:
        sp = int(len(cycles) * 0.75)
        for i, (s, e, _) in enumerate(cycles):
            (train_idx if i < sp else test_idx).extend(range(s, e))
    elif joint == 3:
        for s, e, p in cycles:
            if abs(p - 42) <= 3.0:
                train_idx.extend(range(s, e))
            elif abs(p - 32) <= 3.0:
                test_idx.extend(range(s, e))
    else:  # J1, J5
        for s, e, p in cycles:
            if any(abs(p - t) <= 2.5 for t in (30, 36, 42)):
                train_idx.extend(range(s, e))
            elif any(abs(p - t) <= 2.5 for t in (33, 39, 45)):
                test_idx.extend(range(s, e))
    return np.array(train_idx), np.array(test_idx)


def _build_model(n_inputs: int = 2):
    _, Sequential, Dense, _ = _lazy_tf()
    cfg = NN_CONFIG
    layers = [Dense(cfg.hidden_units[0], activation=cfg.activation, input_shape=(n_inputs,))]
    for units in cfg.hidden_units[1:]:
        layers.append(Dense(units, activation=cfg.activation))
    layers.append(Dense(1))
    model = Sequential(layers)
    model.compile(optimizer=cfg.optimizer, loss="mse")
    return model


def run(paths=PATHS) -> pd.DataFrame:
    """Train the MLP for every joint; return a metrics DataFrame."""
    ensure_output_dirs()
    tf, _, _, EarlyStopping = _lazy_tf()
    np.random.seed(42)
    cfg = NN_CONFIG
    rows = []

    for joint in JOINTS:
        q, v, v_deg, tf_label = _load(joint, paths)
        X = np.column_stack([q, v])
        y = tf_label

        train_idx, test_idx = _cycle_split(v_deg, joint)
        if len(train_idx) == 0 or len(test_idx) == 0:
            print(f"J{joint}: could not build cycle split, skipping")
            continue

        X_pool, y_pool = X[train_idx], y[train_idx]
        X_test, y_test = X[test_idx], y[test_idx]

        perm = np.random.permutation(len(X_pool))
        cut = int(0.90 * len(perm))
        X_train, y_train = X_pool[perm[:cut]], y_pool[perm[:cut]]
        X_val, y_val = X_pool[perm[cut:]], y_pool[perm[cut:]]

        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_val = scaler.transform(X_val)
        X_test_s = scaler.transform(X_test)

        model = _build_model(2)
        es = EarlyStopping(monitor="val_loss", patience=cfg.patience, restore_best_weights=True)
        model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=cfg.max_epochs,
            batch_size=cfg.batch_size,
            callbacks=[es],
            verbose=0,
        )

        y_pred = model.predict(X_test_s, verbose=0).flatten()
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mae = float(mean_absolute_error(y_test, y_pred))
        r2 = float(r2_score(y_test, y_pred))
        print(f"J{joint}  RMSE={rmse:.4f}  MAE={mae:.4f}  R2={r2:.4f}")

        model.save(OUTPUT_ROOT / "models" / f"nn_joint_{joint}.keras")
        rows.append(dict(Joint=f"J{joint}", Test_RMSE=round(rmse, 5),
                         Test_MAE=round(mae, 5), Test_R2=round(r2, 5)))

    df = pd.DataFrame(rows).set_index("Joint")
    out = OUTPUT_ROOT / "params" / "neural_net_metrics.csv"
    df.to_csv(out)
    print(f"\nSaved metrics -> {out}")
    return df


if __name__ == "__main__":
    run()
