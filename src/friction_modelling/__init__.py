"""Friction modelling of a 6-DoF robotic arm (CSIR-CMERI).

Estimation of joint friction using three approaches:
  * Modified Coulomb-Viscous analytical model
  * Black-box deep neural network
  * Physics-informed neural network (LuGre parameter identification)
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
