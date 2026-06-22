"""
default_controller.py — R2H2 Default Engineering Controller
============================================================

This file is the built-in template controller shipped with R2H2.
It delegates entirely to R2H2's ``dynamicControl`` built-in,
which implements:

  • Battery SoC proportional regulator
  • Exponential-smoothing of available power (τ = 30 s)
  • Electrolyser on/off dispatch (turn on least-degraded units first,
    turn off most-degraded units first)

To create a custom controller:
  1. Copy this file and give it a new name (e.g. my_controller.py).
  2. Edit the ``control`` function below.
  3. Assign the new file to a simulation in the Controller tab.

Function signature
------------------
The controller receives:

  units    – list of ElectrolyserUnit objects (one per electrolyser stack)
  battery  – Battery object
  t_out    – TimeOutput object for this hourly step (numpy arrays of length T)
  settings – SimulationSettings object (contains rTimeStep, etc.)

It must return the tuple ``(units, t_out, battery)`` with at minimum:
  t_out.arElectroAvailablePower   – 1-D float array, length T
  t_out.aiIsOn                    – 2-D int array, shape (num_units, T)
"""

from r2h2.r2h2 import dynamicControl


def control(units, battery, t_out, settings):
    """Default controller: delegates to the built-in dynamicControl."""
    return dynamicControl(units, battery, t_out, settings)
