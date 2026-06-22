"""
default_controller.py — R2H2 Default Engineering Controller
============================================================

This file is the built-in template controller shipped with R2H2.
Copy and rename this file to create a custom controller, then assign
it to a simulation in the Controller tab.

Function signature
------------------
The controller receives each hour:

  units    – list of ElectrolyserUnit objects (one per electrolyser stack)
  battery  – Battery object
  t_out    – TimeOutput object for this hourly step
  settings – SimulationSettings object (rTimeStep, rTransientSteps, …)

Required return value: the tuple ``(units, t_out, battery)`` with at minimum:

  t_out.arTotalElectroDemand   – total electrolyser demand [W], 1-D length T
  t_out.aiIsOn                 – ON/OFF status per unit, shape (num_units, T)
  t_out.arProportionPower      – per-unit power fractions, shape (num_units, T)

Key controller inputs available on t_out
-----------------------------------------
  t_out.arAvailablePower       – filtered wind power after ancillary load [W]
  t_out.aiIsOn[:, -1]          – ON/OFF state carried over from the previous hour
  t_out.arTotalElectroOn       – running count of ON units (pre-zeroed)
  t_out.arProportionPower      – per-unit fractions (pre-zeroed)
  t_out.aiWarmedUp             – warm-up mask per unit (1 = warmed up)
  t_out.aiNumOn                – cumulative turn-on count per unit

Key unit attributes
-------------------
  units[i].rMinPower_s         – minimum operating power per unit [W/s]
  units[i].rRatedPower_s       – rated power per unit [W/s]
  units[i].rDeadBandRatio      – dead-band ratio (unit turns on when
                                  available_power > rMinPower_s * rDeadBandRatio)
  units[i].rSummedDegradation  – cumulative degradation (used for priority ranking)
  units[i].rTotalTurnOns       – total turn-on events (for O&M accounting)

Key battery attributes
----------------------
  battery.rControlTargetSoC    – target state-of-charge (0–1, default 0.5)
  battery.rBatteryProportionalGain
  battery.rBatteryRating       – current usable capacity [J]
  battery.arInitialSoC         – SoC at start of this hour (scalar or array)
  battery.arBatteryDemand      – battery power demand [W] — set by controller

Design implemented here
------------------------
  1. Battery SoC proportional regulator
  2. First-order exponential smoothing of available power (τ = 30 s)
  3. Electrolyser on/off dispatch:
       • turn ON  least-degraded units first when more power is available
       • turn OFF most-degraded units first when power drops
  4. Equal power sharing among ON units (proportional fractions)
"""

import numpy as np


def control(units, battery, t_out, settings):
    """Default engineering controller.

    Implements battery SoC regulation, first-order power smoothing, and
    degradation-priority electrolyser on/off dispatch.
    """
    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------
    total_available_power = np.asarray(t_out.arAvailablePower, dtype=float)
    T = len(total_available_power)

    num_units = len(units)

    # Seed all timesteps from the last known ON/OFF state so the dispatch
    # loop starts from a fully populated, consistent baseline.
    prev_on = np.asarray(t_out.aiIsOn[:, -1], dtype=int).reshape(num_units, 1)
    t_out.aiIsOn[:, :] = prev_on

    # Degradation determines dispatch priority (least degraded turned on first,
    # most degraded turned off first).
    degradation = np.array([u.rSummedDegradation for u in units], dtype=float)

    initial_soc      = np.asarray(battery.arInitialSoC, dtype=float)
    battery_capacity = float(battery.rBatteryRating)

    # ------------------------------------------------------------------
    # 1. Battery SoC proportional regulator
    # ------------------------------------------------------------------
    soc_target = battery.rControlTargetSoC   # target SoC (0–1)
    rBatteryProportion = np.clip(
        soc_target - initial_soc,
        -(1.0 - soc_target),
        soc_target,
    )
    # Positive demand charges the battery; negative demand discharges it.
    battery.arBatteryDemand = (
        total_available_power * rBatteryProportion
    ) * battery.rBatteryProportionalGain

    # Limit battery charge/discharge rate to 10 % of capacity per second
    # and prevent discharging below zero SoC.
    per_sec_limit = 0.1 * battery_capacity / 3600.0
    battery.arBatteryDemand = np.clip(
        battery.arBatteryDemand, -per_sec_limit, per_sec_limit
    )
    if float(np.atleast_1d(initial_soc).ravel()[-1]) <= 0.0:
        battery.arBatteryDemand = np.clip(battery.arBatteryDemand, 0.0, per_sec_limit)

    # Power available to electrolysers after battery charging/discharging.
    t_out.arElectroAvailablePowerA = np.maximum(
        t_out.arAvailablePower - battery.arBatteryDemand, 0.0
    )

    # ------------------------------------------------------------------
    # 2. First-order exponential smoothing (τ = 30 s)
    #    Smooths the power signal before dispatch decisions to avoid
    #    rapid on/off cycling from wind fluctuations.
    # ------------------------------------------------------------------
    tau   = 30                          # time constant [s]
    dt    = settings.rTimeStep
    alpha = dt / (tau + dt)
    t_out.arElectroAvailablePower = np.zeros_like(t_out.arElectroAvailablePowerA)
    t_out.arElectroAvailablePower[0] = t_out.arElectroAvailablePowerA[0]
    for k in range(1, T):
        t_out.arElectroAvailablePower[k] = (
            alpha * t_out.arElectroAvailablePowerA[k]
            + (1.0 - alpha) * t_out.arElectroAvailablePower[k - 1]
        )
    t_out.rPreviousValue = float(t_out.arElectroAvailablePower[-1])

    # ------------------------------------------------------------------
    # 3. On/off dispatch
    # ------------------------------------------------------------------
    rMin   = units[0].rMinPower_s
    rRated = units[0].rRatedPower_s

    # Maximum units that could run given available power (floor ÷ min power).
    arMaxElectroSum = np.floor(t_out.arElectroAvailablePower / rMin).astype(int)
    # Minimum units required to absorb available power (ceil ÷ rated power).
    arMinElectroSum = np.ceil(t_out.arElectroAvailablePower / rRated).astype(int)

    step0 = int(settings.rTransientSteps)
    t_out.aiIsOn[:, step0 - 1] = t_out.aiIsOn[:, -1]
    t_out.arTotalElectroOn[step0 - 1] = np.sum(t_out.aiIsOn[:, step0 - 1])
    if t_out.arTotalElectroOn[step0 - 1] > 0:
        t_out.arProportionPower[:, step0 - 1] = (
            t_out.aiIsOn[:, step0 - 1] / t_out.arTotalElectroOn[step0 - 1]
        )

    for k in range(step0, T):
        t_out.aiIsOn[:, k] = t_out.aiIsOn[:, k - 1]
        total_on_prev   = t_out.arTotalElectroOn[k - 1]
        available_power = t_out.arElectroAvailablePower[k]

        if arMinElectroSum[k] > total_on_prev and available_power > rMin * units[0].rDeadBandRatio:
            # More power available — turn on least-degraded idle units first.
            rank = np.argsort(degradation)
            need = arMinElectroSum[k] - total_on_prev
            for idx in rank:
                if need <= 0:
                    break
                if t_out.aiIsOn[idx, k] == 0:
                    t_out.aiIsOn[idx, k] = 1
                    t_out.aiNumOn[idx] += 1
                    # Mark warm-up window (10 min) for the newly started unit.
                    endi = min(T, k + int(10 * 60 / dt))
                    t_out.aiWarmedUp[idx, k:endi] = 0
                    units[idx].rTotalTurnOns += 1
                    need -= 1
            t_out.arTotalElectroOn[k] = np.sum(t_out.aiIsOn[:, k])

        elif arMaxElectroSum[k] < total_on_prev:
            # Power too low to keep all units above minimum — turn off
            # most-degraded units first to protect healthier stacks.
            rank = np.argsort(degradation)
            need = int(total_on_prev - arMaxElectroSum[k])
            for idx in rank:
                if need <= 0:
                    break
                if t_out.aiIsOn[idx, k] == 1:
                    t_out.aiIsOn[idx, k] = 0
                    need -= 1
            t_out.arTotalElectroOn[k] = np.sum(t_out.aiIsOn[:, k])

        else:
            t_out.arTotalElectroOn[k] = total_on_prev

        # Equal sharing: each ON unit receives an equal fraction of total power.
        if t_out.arTotalElectroOn[k] > 0:
            t_out.arProportionPower[:, k] = (
                t_out.aiIsOn[:, k] / t_out.arTotalElectroOn[k]
            )

    # ------------------------------------------------------------------
    # Required output: total demand profile clipped to physical bounds
    # ------------------------------------------------------------------
    t_out.arTotalElectroDemand = np.clip(
        t_out.arElectroAvailablePower,
        rMin   * t_out.arTotalElectroOn,
        rRated * t_out.arTotalElectroOn,
    )

    return units, t_out, battery

