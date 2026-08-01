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

## Quick start (Windows, no Docker, no Conda)

Just one script. Double-click, or from a terminal:

```bat
run.bat
```

- **First run:** creates `cmerivenv` on **Python 3.13**, installs everything
  (including TensorFlow), then drops you into a menu.
- **Every run after that:** skips straight to the menu.