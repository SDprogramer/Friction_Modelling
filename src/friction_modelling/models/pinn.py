"""Physics-Informed Neural Network for LuGre parameter identification.

A small MLP maps (v, q) -> constrained LuGre parameters
(sigma0, sigma1, sigma2, Fc, Fs, vs, C0). The network is trained with a
steady-state LuGre physics loss anchored by the already-identified
Coulomb-Viscous reference model.
"""
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd

from friction_modelling.config import (
    JOINTS, N_GEAR, OUTPUT_ROOT, PATHS, PINN_CONFIG, REF_PARAMS, ensure_output_dirs,
)

warnings.filterwarnings("ignore")


def _lazy_tf():
    import tensorflow as tf
    from tensorflow.keras import Model, layers

    tf.random.set_seed(42)
    return tf, Model, layers


def _load_joint(joint: int, paths=PATHS):
    df = pd.read_csv(paths.vel_file(joint)).dropna()
    v = np.deg2rad(df[f"v{joint}"].values).astype(np.float32)
    q = np.deg2rad(df[f"q{joint}"].values).astype(np.float32)
    mt = df[f"m_t_{joint}"].values.astype(np.float32)
    jts = df[f"jts{joint}"].values.astype(np.float32)
    tau_f = (N_GEAR * mt - (-jts)).astype(np.float32)
    return v, q, tau_f


def _make_pinn():
    tf, Model, layers = _lazy_tf()

    class LuGrePINN(Model):
        def __init__(self):
            super().__init__(name="LuGrePINN")
            act = "tanh"
            self.hidden = tf.keras.Sequential([
                layers.Dense(64, activation=act),
                layers.Dense(64, activation=act),
                layers.Dense(32, activation=act),
                layers.Dense(8, activation=act),
            ])
            self.out_layer = layers.Dense(7, activation=None)

        def call(self, X, training=False):
            h = self.hidden(X, training=training)
            raw = self.out_layer(h)
            sp = tf.nn.softplus
            sigma0 = sp(raw[:, 0]) * 1e3
            sigma1 = sp(raw[:, 1]) * 10.0
            sigma2 = sp(raw[:, 2]) * 10.0
            Fc = sp(raw[:, 3]) * 5.0
            dFs = sp(raw[:, 4]) * 2.0
            Fs = Fc + dFs
            vs = sp(raw[:, 5]) * 0.05 + 1e-4
            C0 = raw[:, 6]
            return dict(sigma0=sigma0, sigma1=sigma1, sigma2=sigma2,
                        Fc=Fc, Fs=Fs, vs=vs, C0=C0)

    return LuGrePINN()


def run(paths=PATHS) -> pd.DataFrame:
    """Identify LuGre parameters for every joint via the PINN."""
    ensure_output_dirs()
    tf, _, _ = _lazy_tf()
    cfg = PINN_CONFIG
    rows = []

    def lugre_ss(v, p):
        sv = tf.sign(v)
        exp_term = tf.exp(-tf.square(v / (p["vs"] + 1e-8)))
        return (p["Fc"] * sv + (p["Fs"] - p["Fc"]) * sv * exp_term
                + p["sigma2"] * v + p["C0"])

    def ref_friction(v, q, joint):
        rp = REF_PARAMS[joint]
        v_eff = v + rp["Cp"] * q
        return rp["Tc"] * tf.tanh(v_eff / rp["Vs"]) + rp["Bv"] * v_eff + rp["C0_ref"]

    for joint in JOINTS:
        v_all, q_all, tau_all = _load_joint(joint, paths)
        n = len(v_all)
        tr_end = int(cfg.train_frac * n)
        val_end = int((cfg.train_frac + cfg.val_frac) * n)

        v_tr, q_tr, tau_tr = v_all[:tr_end], q_all[:tr_end], tau_all[:tr_end]
        v_te, q_te, tau_te = v_all[val_end:], q_all[val_end:], tau_all[val_end:]

        v_mean, v_std = v_tr.mean(), v_tr.std() + 1e-8
        q_mean, q_std = q_tr.mean(), q_tr.std() + 1e-8

        def norm(v, q):
            return tf.cast(np.column_stack([(v - v_mean) / v_std, (q - q_mean) / q_std]), tf.float32)

        X_tr = norm(v_tr, q_tr)
        X_te = norm(v_te, q_te)
        v_tr_t = tf.constant(v_tr)
        q_tr_t = tf.constant(q_tr)
        tau_tr_t = tf.constant(tau_tr)

        model = _make_pinn()
        opt = tf.keras.optimizers.Adam(cfg.lr)

        best_loss, wait = np.inf, 0
        for epoch in range(cfg.epochs):
            with tf.GradientTape() as tape:
                params = model(X_tr, training=True)
                pred = lugre_ss(v_tr_t, params)
                phys = tf.reduce_mean(tf.keras.losses.huber(tau_tr_t, pred, delta=1.0))
                ref = ref_friction(v_tr_t, q_tr_t, joint)
                ref_l = cfg.ref_weight * tf.reduce_mean(tf.square(pred - ref))
                loss = phys + ref_l
            grads = tape.gradient(loss, model.trainable_variables)
            opt.apply_gradients(zip(grads, model.trainable_variables))

            lv = float(loss.numpy())
            if lv < best_loss - 1e-5:
                best_loss, wait = lv, 0
            else:
                wait += 1
                if wait >= cfg.patience:
                    break

        # Evaluate on test set
        params_te = model(X_te, training=False)
        pred_te = lugre_ss(tf.constant(v_te), params_te).numpy()
        rmse = float(np.sqrt(np.mean((tau_te - pred_te) ** 2)))

        p_mean = {k: float(np.mean(v.numpy())) for k, v in params_te.items()}
        print(f"J{joint}  sigma0={p_mean['sigma0']:.2f}  Fc={p_mean['Fc']:.3f}"
              f"  Fs={p_mean['Fs']:.3f}  vs={p_mean['vs']:.4f}  | test RMSE={rmse:.4f}")

        rows.append(dict(
            Joint=f"J{joint}",
            sigma0=round(p_mean["sigma0"], 4),
            sigma1=round(p_mean["sigma1"], 4),
            sigma2=round(p_mean["sigma2"], 4),
            Fc=round(p_mean["Fc"], 4),
            Fs=round(p_mean["Fs"], 4),
            vs=round(p_mean["vs"], 5),
            C0=round(p_mean["C0"], 4),
            Test_RMSE=round(rmse, 4),
        ))

    df = pd.DataFrame(rows).set_index("Joint")
    out = OUTPUT_ROOT / "params" / "pinn_lugre_params.csv"
    df.to_csv(out)
    print(f"\nSaved LuGre parameters -> {out}")
    return df


if __name__ == "__main__":
    run()
