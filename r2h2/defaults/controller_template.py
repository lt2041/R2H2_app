"""R2H2 Engineering Controller Template
========================================
Copy this file to  ``<data_root>/controllers/``  with a descriptive name
(e.g. ``my_strategy.py``) then select it from the
**Simulation Settings → Engineering Controller** dropdown.

Required interface
------------------
The module must expose a callable named ``control`` with the signature::

    def control(units, battery, t_out, settings) -> tuple[list, TimeOutputs, Battery]

The function is called once per simulated hour, replacing the built-in
``dynamicControl`` dispatch algorithm.

Parameters
----------
units : list
    One :class:`ElectrolyserUnit`-like object per controllable unit.
    Key attributes (read / write):

    ``rSummedDegradation``  – accumulated degradation [dimensionless]
    ``rMinPower_s``         – minimum unit power [W]
    ``rRatedPower_s``       – rated unit power [W]
    ``rDeadBandRatio``      – on/off dead-band multiplier [-]
    ``rTimeConst``          – first-order time constant [s]
    ``rTotalTurnOns``       – cumulative on-count (increment on each start)

battery : Battery-like object
    Key attributes (read / write):

    ``arInitialSoC``              – current state-of-charge [0–1]
    ``rSoCRef``                   – target SoC [0–1]
    ``rBatteryRating``            – energy capacity [J]
    ``rBatteryProportionalGain``  – proportional gain for SoC controller
    ``arBatteryDemand``           – 1-D array (shape T) written by this fn [W]

t_out : TimeOutputs-like object
    Arrays that must be populated before returning (all shape (T,) unless noted):

    ``arElectroAvailablePowerA``  – battery-adjusted available power [W]
    ``arElectroAvailablePower``   – low-pass filtered available power [W]
    ``rPreviousValue``            – last filtered value (scalar, carry-over)
    ``arTotalElectroOn``          – units on at each timestep [−]
    ``arProportionPower``         – (n_units × T) power share per unit [−]
    ``aiIsOn``                    – (n_units × T) on/off flag [0/1]
    ``aiWarmedUp``                – (n_units × T) warm-up flag (0 = warming)
    ``aiNumOn``                   – (n_units,) cumulative on-count per unit

    Read-only inputs on t_out:

    ``arAvailablePower``          – available wind power entering this hour [W]

settings : Simulation-like object
    Read-only:

    ``rTimeStep``       – simulation time step [s]
    ``rTransientSteps`` – initial transient steps to skip (integer)

Returns
-------
tuple
    ``(units, t_out, battery)``  – the same objects, mutated as needed.

Notes
-----
* ``numpy`` is the only external dependency assumed to be available.
* Do **not** import Django models here; this file runs inside the simulation
  thread and must remain engine-agnostic.
* Keep the function deterministic: avoid global state so that multi-year
  simulations replicate correctly.
"""

import numpy as np


# ---------------------------------------------------------------------------
# Internal helpers (copy / modify freely)
# ---------------------------------------------------------------------------

def _first_order_lp(x: np.ndarray, tau: float, dt: float) -> np.ndarray:
    """Causal first-order low-pass filter.

    Parameters
    ----------
    x   : 1-D input array
    tau : time constant [s]
    dt  : sample interval [s]

    Returns
    -------
    y : filtered array, same shape as x
    """
    alpha = dt / (tau + dt)
    y = np.empty_like(x)
    y[0] = x[0]
    for k in range(1, len(x)):
        y[k] = alpha * x[k] + (1.0 - alpha) * y[k - 1]
    return y


# ---------------------------------------------------------------------------
# Main control function — edit this to implement your strategy
# ---------------------------------------------------------------------------

def control(units, battery, t_out, settings):
    """Default engineering controller.

    Implements:
    1. Proportional battery SoC regulation (adds/removes power to/from buffer).
    2. First-order low-pass filtering of the electrolyser-available power.
    3. Damage-ranked on/off dispatch of electrolyser units.
    4. Equal proportional power sharing among active units.

    Modify any section below to implement a custom control strategy.
    """

    # ── 1. Battery SoC proportional control ─────────────────────────────────
    battery.arBatteryDemand = np.zeros_like(t_out.arAvailablePower)

    soc_error = np.clip(
        battery.rSoCRef - battery.arInitialSoC,
        -(1.0 - battery.rSoCRef),
        battery.rSoCRef,
    )
    battery.arBatteryDemand = (
        t_out.arAvailablePower * soc_error * battery.rBatteryProportionalGain
    )

    # Rate-limit battery demand (≤ 10 % of capacity per second)
    per_sec_limit = 0.1 * battery.rBatteryRating / 3600.0
    battery.arBatteryDemand = np.clip(
        battery.arBatteryDemand, -per_sec_limit, per_sec_limit
    )
    # Never discharge a fully empty battery
    if battery.arInitialSoC <= 0.0:
        battery.arBatteryDemand = np.clip(battery.arBatteryDemand, 0.0, per_sec_limit)

    # Power available to electrolysers after battery buffer
    t_out.arElectroAvailablePowerA = np.maximum(
        t_out.arAvailablePower - battery.arBatteryDemand, 0.0
    )

    # ── 2. Low-pass filter ───────────────────────────────────────────────────
    tau = units[0].rTimeConst
    dt  = float(settings.rTimeStep)
    t_out.arElectroAvailablePower = _first_order_lp(
        t_out.arElectroAvailablePowerA, tau, dt
    )
    t_out.rPreviousValue = float(t_out.arElectroAvailablePower[-1])

    # ── 3. On/off dispatch ───────────────────────────────────────────────────
    rMin   = units[0].rMinPower_s
    rRated = units[0].rRatedPower_s

    # How many units are needed at minimum / maximum power?
    arMaxOn = np.floor(t_out.arElectroAvailablePower / rMin).astype(int)
    arMinOn = np.ceil(t_out.arElectroAvailablePower / rRated).astype(int)

    T     = len(t_out.arElectroAvailablePower)
    step0 = int(settings.rTransientSteps)

    # Rank units by damage (least damaged → switch on first, switch off last)
    damage = np.array([u.rSummedDegradation for u in units], dtype=float)
    rank   = np.argsort(damage)          # ascending: rank[0] = least damaged

    # Carry-over from previous hour's last time-step
    t_out.aiIsOn[:, step0 - 1] = t_out.aiIsOn[:, -1]
    t_out.arTotalElectroOn[step0 - 1] = np.sum(t_out.aiIsOn[:, step0 - 1])
    if t_out.arTotalElectroOn[step0 - 1] > 0:
        t_out.arProportionPower[:, step0 - 1] = (
            t_out.aiIsOn[:, step0 - 1] / t_out.arTotalElectroOn[step0 - 1]
        )

    dead_band_threshold = rMin * units[0].rDeadBandRatio
    warmup_steps = int(10 * 60 / dt)    # 10-minute warm-up at any time step

    for k in range(step0, T):
        t_out.aiIsOn[:, k] = t_out.aiIsOn[:, k - 1]
        n_on     = t_out.arTotalElectroOn[k - 1]
        p_avail  = t_out.arElectroAvailablePower[k]

        if arMinOn[k] > n_on and p_avail > dead_band_threshold:
            # Need to switch units ON (start least-damaged first)
            need = int(arMinOn[k] - n_on)
            for idx in rank:
                if need <= 0:
                    break
                if t_out.aiIsOn[idx, k] == 0:
                    t_out.aiIsOn[idx, k] = 1
                    t_out.aiNumOn[idx] += 1
                    endi = min(T, k + warmup_steps)
                    t_out.aiWarmedUp[idx, k:endi] = 0
                    units[idx].rTotalTurnOns += 1
                    need -= 1
            t_out.arTotalElectroOn[k] = np.sum(t_out.aiIsOn[:, k])

        elif arMaxOn[k] < n_on:
            # Need to switch units OFF (shut down least-damaged first)
            need = int(n_on - arMaxOn[k])
            for idx in rank:
                if need <= 0:
                    break
                if t_out.aiIsOn[idx, k] == 1:
                    t_out.aiIsOn[idx, k] = 0
                    need -= 1
            t_out.arTotalElectroOn[k] = np.sum(t_out.aiIsOn[:, k])

        else:
            t_out.arTotalElectroOn[k] = n_on

        # ── 4. Equal power sharing ───────────────────────────────────────────
        if t_out.arTotalElectroOn[k] > 0:
            t_out.arProportionPower[:, k] = (
                t_out.aiIsOn[:, k] / t_out.arTotalElectroOn[k]
            )

    return units, t_out, battery
