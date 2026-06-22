# Dynamic Controller User Guide

## Overview

R2H2 supports two controller modes:

- Built-in controller: dynamicControl
- Custom controller: a user-provided Python function named control

The controller is executed once per simulation hour and generates per-second dispatch arrays for that hour.

If a custom controller is selected for a simulation, R2H2 loads it and calls its control function. If loading or execution fails, R2H2 automatically falls back to the built-in dynamicControl.

## Where The Controller Runs

For each simulation hour:

1. The engine initializes hourly output arrays in t_out.
2. The controller is called to set total demand, on/off state, and per-unit allocation.
3. The electro-thermal step uses the controller outputs to compute current, voltage, hydrogen, heat, and thermal state.

Controller entry points are implemented in r2h2/r2h2.py:

- dynamicControl: built-in behavior
- _call_controller_safe: custom controller wrapper with validation and fallback
- runElectroStackStep1: per-hour execution path

## Custom Controller Function Contract

Your controller file must define this function:

```python
def control(units, battery, t_out, settings):
    # update units, battery, t_out
    return units, t_out, battery
```

### Required Inputs

Your function receives four objects:

1. units
- List of electrolyser unit objects.
- Commonly used fields include:
  - rSummedDegradation
  - rMinPower_s
  - rRatedPower_s
  - rDeadBandRatio
  - rTotalTurnOns

2. battery
- Battery state and control parameters.
- Commonly used fields include:
  - arInitialSoC
  - rControlTargetSoC
  - rBatteryProportionalGain
  - rBatteryRating
  - arBatteryDemand

3. t_out
- Hourly per-second output container, pre-initialized before controller call.
- Minimum arrays your controller must set:
  - arTotalElectroDemand
  - aiIsOn
  - arProportionPower
- Common optional arrays:
  - arTotalElectroOn
  - arElectroAvailablePowerA
  - arElectroAvailablePower

4. settings
- Simulation settings.
- Commonly used fields include:
  - rTimeStep
  - rTransientSteps

### Required Return Value

Return exactly a 3-tuple:

- units
- t_out
- battery

### Validation Rules Enforced By R2H2

R2H2 validates the returned data. If validation fails, it falls back to built-in dynamicControl.

Checks include:

- Returned unit count must equal expected number of units.
- t_out.arTotalElectroDemand must exist and have length T.
- t_out.aiIsOn must have shape (num_units, T).
- t_out.arProportionPower must have shape (num_units, T).
- t_out.arTotalElectroOn is optional. If omitted, it is derived from aiIsOn.
- arTotalElectroDemand, aiIsOn, and arProportionPower must not contain NaN or Inf.
- battery.arBatteryDemand is optional. If omitted, R2H2 infers it as:
  - arBatteryDemand = arAvailablePower - arElectroAvailablePowerA
  - If arElectroAvailablePowerA is not provided, arTotalElectroDemand is used.

### Minimal Required Controller Outputs

In practice, the minimum outputs your controller must set are:

- t_out.arTotalElectroDemand
- t_out.aiIsOn
- t_out.arProportionPower

R2H2 can derive these optional outputs when absent:

- t_out.arTotalElectroOn
- battery.arBatteryDemand

### Power Consistency Notes

- In built-in dynamicControl, electrolyser input power before smoothing is computed as:
  - arElectroAvailablePowerA = max(arAvailablePower - arBatteryDemand, 0)
- For custom controllers, arBatteryDemand is primarily a dispatch trace. If you do not set it,
  R2H2 infers it from your outputs for logging/debugging.
- Battery state update is computed from residual power using:
  - P_batt = arAvailablePower - arTotalElectroDemand
  This happens in the battery step after controller dispatch.

Per-unit demand mapping:

- Initial per-unit demand target is computed as:
  - arElectroDemand[i, :] = arProportionPower[i, :] * arTotalElectroDemand
- Then physical guards/ramping can adjust per-unit demand and proportions to keep
  execution feasible.

### Electrolyser Limits And Residual Handling

Outside the controller, R2H2 applies additional guards and balancing logic:

- Total electrolyser demand is clipped to fleet bounds based on active units:
  - lower bound: rMinPower_s * arTotalElectroOn
  - upper bound: rRatedPower_s * arTotalElectroOn
- Per-unit demand is capped at rRatedPower_s.
- Per-unit minimum power is enforced for ON units.
- Per-unit demand is also constrained by ramp up/down rates.

Automatic ON-count correction:

- If too many units are ON to satisfy individual minimum power, R2H2 will
  automatically turn OFF the lowest-priority units (based on controller
  proportion weights) before electro-thermal execution.
- Demand is then re-allocated across remaining ON units within [min, max]
  per-unit bounds.

What this means in practice:

- If requested electrolyser demand is too high, it is clipped down and residual power
  tends to go to battery charging (subject to battery limits).
- If requested demand is too low for the enforced floor, battery discharge may be
  required to supply the shortfall (subject to battery limits).
- Battery dynamics still apply after clipping/ramping via:
  - P_batt = arAvailablePower - arTotalElectroDemand

Important nuance:

- Minimum and maximum are now enforced at both fleet and per-unit execution level,
  outside the controller.
- If the requested dispatch is infeasible with current ON count and bounds,
  the engine modifies ON state and re-allocates demand to keep execution physical.

Important:

- The built-in dynamicControl includes a battery SoC regulator that drives SoC toward
  rControlTargetSoC using battery.rBatteryProportionalGain.
- If you do not want this built-in SoC regulation behavior, set:
  - rBatteryProportionalGain = 0
  This disables the proportional battery-demand action from that regulator.

### Timeout And Error Handling

- A custom control call has a wall-clock timeout of 30 seconds.
- Any exception in control causes fallback to built-in dynamicControl.

## Variables Set By Built-In dynamicControl

The built-in controller sets or updates these primary variables:

Battery-related:

- battery.arBatteryDemand

Power availability:

- t_out.arElectroAvailablePowerA
- t_out.arElectroAvailablePower
- t_out.rPreviousValue

Dispatch state:

- t_out.aiIsOn
- t_out.arTotalElectroOn
- t_out.arProportionPower
- t_out.aiNumOn
- t_out.aiWarmedUp
- units[i].rTotalTurnOns

## Minimal Custom Controller Example

This simple example sets the required outputs.

```python
import numpy as np


def control(units, battery, t_out, settings):
    T = len(t_out.arAvailablePower)
  num_units = len(units)

  # Required output 1: total fleet demand [W], length T
  t_out.arTotalElectroDemand = np.asarray(t_out.arAvailablePower, dtype=float).copy()

  # Required output 2: ON/OFF matrix, shape (num_units, T)
  t_out.aiIsOn[:, :] = 0
    step0 = int(settings.rTransientSteps)
    t_out.aiIsOn[:, step0 - 1] = t_out.aiIsOn[:, -1]

    for k in range(step0, T):
        t_out.aiIsOn[:, k] = t_out.aiIsOn[:, k - 1]

  # Example: turn all units ON after transient
  t_out.aiIsOn[:, step0:] = 1

  # Required output 3: per-unit fractions, shape (num_units, T)
  t_out.arProportionPower[:, :] = 0.0
  on_count = np.sum(t_out.aiIsOn, axis=0).astype(float)
  on_mask = on_count > 0
  if np.any(on_mask):
    t_out.arProportionPower[:, on_mask] = (
      t_out.aiIsOn[:, on_mask] / on_count[on_mask]
    )

    return units, t_out, battery
```

Note:

- This is intentionally simple and does not include turn-on/off decision logic.
- Production controllers should include robust dispatch logic and guardrails.

## Controller File Management In The UI

When creating controller files through the dashboard:

- Extension must be .py.
- Name stem must match this pattern:
  - starts with a lowercase letter
  - contains only lowercase letters, digits, and underscores
- Path traversal is blocked.
- Empty files are rejected.
- Syntax errors are blocked.
- Potentially dangerous patterns are flagged as warnings.

Default controller protection:

- default_controller.py cannot be created as a new overwrite target.
- default_controller.py cannot be renamed.

## Recommended Development Workflow

1. Start from the minimal template above.
2. Implement dispatch updates for:
   - t_out.arTotalElectroDemand
   - t_out.aiIsOn
   - t_out.arProportionPower
3. Optionally set:
  - t_out.arTotalElectroOn
  - t_out.arElectroAvailablePowerA
  - t_out.arElectroAvailablePower
  - battery.arBatteryDemand
4. Test with a short simulation window first.
5. Confirm no fallback warnings appear.
6. Scale to longer runs only after behavior is stable.

## Troubleshooting

Symptom: Controller is ignored and built-in behavior is used.

Possible causes:

- Missing control function.
- Wrong return type or tuple size.
- Array shape mismatch.
- NaN/Inf values in key arrays.
- Runtime exception in control.
- Control call exceeded timeout.

What to check first:

1. Controller file defines control(units, battery, t_out, settings).
2. Returned tuple is exactly (units, t_out, battery).
3. Required arrays (arTotalElectroDemand, aiIsOn, arProportionPower) exist and have expected dimensions.
4. No invalid numeric values are produced.

Physical sanity checks:

- arSpillPower should normally remain near zero in physically consistent runs.
- If arSpillPower has sustained significant magnitude, treat this as a model/control
  consistency issue and review controller commands, electrolyser bounds, and battery limits.

## 1Hz Controller Debug Logging

When 1Hz collection is enabled, R2H2 now writes controller-oriented debug traces
to /time_series_1hz in the output HDF5 file.

Controller inputs captured:

- controller_input_arAvailablePower (1-D, length n_seconds)
- controller_input_aiIsOn (2-D, shape [n_seconds, n_units])
- controller_input_initial_soc (1-D, length n_seconds)

Controller outputs captured:

- controller_output_arBatteryDemand (1-D, length n_seconds)
- controller_output_arElectroAvailablePowerA (1-D, length n_seconds)
- controller_output_arElectroAvailablePower (1-D, length n_seconds)
- controller_output_arTotalElectroOn (1-D, length n_seconds)
- controller_output_aiIsOn (2-D, shape [n_seconds, n_units])
- controller_output_arProportionPower (2-D, shape [n_seconds, n_units])

Optional developer buffers captured (if set by your controller):

- arBuffer1 through arBuffer20 (each 1-D, length n_seconds)

End-of-hour buffer mapping (optional):

- You can define ``end_hour_buffer_map`` (or ``END_HOUR_BUFFER_MAP``) in your
  controller module to map any ``t_out`` variable into ``arBuffer`` slots using
  the final value of each simulated hour.
- This mapping is applied after ``runElectroStackStep1`` and subsequent hourly
  post-processing (for example battery update), so values represent end-of-hour
  state.
- Mapping values can be:
  - a string (name of a ``t_out`` attribute)
  - a callable ``fn(t_out)`` returning a scalar/array-like
  - a scalar/array-like constant
- For array-like values, R2H2 uses the last element for that hour and fills the
  full 1Hz segment of that hour with that scalar.

Example:

```python
end_hour_buffer_map = {
    'arBuffer1': 'arEta_system_total',   # final system efficiency for the hour
    'arBuffer2': 'arT_stack',            # final average stack temperature
    'arBuffer3': lambda t: np.mean(t.arTotalElectroOn),
}
```

System-populated non-essential buffer channel:

- arBuffer20 is auto-populated with arTotalElectroOn when your controller does
  not set arBuffer20 explicitly. This keeps a common non-essential trace in the
  same buffer-based logging model.

Notes:

- These traces are snapshots around the controller call in each simulated hour.
- This makes it easier to compare what your custom controller received versus what it wrote.
- 1Hz collection windows are not hard-limited by duration, but long windows can
  generate very large output files.
- For ranges longer than approximately 3 months, use with care.

### Using arBuffer1..arBuffer20 For Debugging

Custom controllers can write temporary debug signals to any of:

- t_out.arBuffer1
- t_out.arBuffer2
- ...
- t_out.arBuffer20

Quick start workflow:

1. Pick 2-5 buffers for the values you want to inspect.
2. Assign one signal per buffer inside control().
3. Run a short simulation with 1 Hz logging enabled.
4. Open /time_series_1hz in the output HDF5 and inspect those buffers.

Recommended channel plan:

- arBuffer1: primary control signal (for example, power command)
- arBuffer2: battery or SoC-related signal
- arBuffer3: unit count or switching metric
- arBuffer4: constraint margin (headroom, limit proximity)
- arBuffer5: mode/state code (cast to float if needed)
- arBuffer20: reserved default system channel (arTotalElectroOn)

Rules:

- If a buffer is not set (None), it is not written.
- If a buffer is a scalar, R2H2 broadcasts it across the hour.
- If a buffer is an array/list, its length must match the hourly 1 Hz time axis.
  Mismatched lengths are skipped.
- arBuffer20 is reserved as a default system buffer for arTotalElectroOn.
  If you set arBuffer20 yourself, your values are used instead.

Shape guidance:

- Preferred: 1-D arrays of length T (T = number of 1 Hz timesteps in the hour).
- Scalars are valid and auto-broadcast to length T.
- Avoid 2-D arrays for buffers; flattening may hide mistakes.

Practical tips:

- Keep a stable meaning for each buffer across runs so plots are comparable.
- Reuse the same channel mapping between controller versions.
- Start with a small set of buffers, then add more only when needed.
- Use finite numeric values only; NaN and Inf make debugging harder.

Example:

```python
def control(units, battery, t_out, settings):
    # Required outputs
  t_out.arTotalElectroDemand = t_out.arAvailablePower.copy()
    t_out.aiIsOn[:, :] = 1
  n_on = np.sum(t_out.aiIsOn, axis=0).astype(float)
  t_out.arProportionPower[:, :] = t_out.aiIsOn / n_on

    # Optional debug buffers
  t_out.arBuffer1 = t_out.arTotalElectroDemand                 # total electrolyser demand
    t_out.arBuffer2 = battery.arInitialSoC                       # scalar -> broadcast by R2H2
    t_out.arBuffer3 = t_out.aiIsOn.sum(axis=0)                   # units on at each timestep
  t_out.arBuffer4 = t_out.arAvailablePower - t_out.arTotalElectroDemand
    # Leave arBuffer20 unset to get default arTotalElectroOn there

    return units, t_out, battery
```

  Example: creating fixed-length arrays explicitly

  ```python
  import numpy as np


  def control(units, battery, t_out, settings):
    T = len(t_out.arAvailablePower)

    # Required outputs
    t_out.arTotalElectroDemand = t_out.arAvailablePower.copy()
    t_out.aiIsOn[:, :] = 1
    n_on = np.sum(t_out.aiIsOn, axis=0).astype(float)
    t_out.arProportionPower[:, :] = t_out.aiIsOn / n_on

    # Explicit debug arrays (recommended when building new controllers)
    t_out.arBuffer1 = t_out.arTotalElectroDemand.copy()
    t_out.arBuffer2 = np.full(T, float(battery.arInitialSoC))
    t_out.arBuffer3 = np.sum(t_out.aiIsOn, axis=0).astype(float)

    return units, t_out, battery
  ```

  ### Inspecting Buffers In Python

  Use this example to inspect available buffer channels and plot selected traces
  from /time_series_1hz in an output HDF5 file. Note you may need to run 
  ```python
pip install plotly-resampler
  ```
prior to using the code below
  ```python
import h5py
import pandas as pd

import plotly.graph_objects as go
from plotly_resampler import FigureResampler
import plotly.subplots as sp
import webbrowser

# Adjust this to be the path to your h5 file
h5_path = "/home/ajs2007/Downloads/run_47_Default_Model_20260619-105234.h5"

with h5py.File(h5_path, "r") as f:
    if "time_series_1hz" not in f:
        raise RuntimeError("No /time_series_1hz group found in this file.")

    ts = f["time_series_1hz"]
    keys = sorted(ts.keys())

    print("Available datasets:")
    for k in keys:
        print("  ", k, ts[k].shape)

    #  Convert seconds → datetime
    t = ts["time_indices"][:]
    t = pd.to_datetime(t, unit="s")

    # Channels to plot
    plot_keys = [
        "arBuffer1","arBuffer2","arBuffer3","arBuffer4","arBuffer5",
        "arBuffer6","arBuffer7","arBuffer8","arBuffer9","arBuffer10",
        "arBuffer11","arBuffer12","arBuffer13","arBuffer14","arBuffer15",
        "arBuffer16","arBuffer17","arBuffer18","arBuffer19","arBuffer20",
        "controller_output_arBatteryDemand",
        "controller_output_arElectroAvailablePower",
    ]
    plot_keys = [k for k in plot_keys if k in ts]

    if not plot_keys:
        raise RuntimeError("No selected channels found.")

    # Create subplot figure
    base_fig = sp.make_subplots(rows=len(plot_keys), cols=1, shared_xaxes=True)

    fig = FigureResampler(base_fig)

    for i, key in enumerate(plot_keys, start=1):
        y = ts[key][:]

        if y.ndim == 2:
            y_plot = y[:, 0]
        else:
            y_plot = y

        fig.add_trace(
            go.Scattergl(name=key, mode='lines'),
            hf_x=t,
            hf_y=y_plot,
            row=i,
            col=1
        )

#  Layout
fig.update_layout(
    height=300 * len(plot_keys),
    title="Interactive Time Series (Resampled)"
)

#   Dynamic time scaling for x-axis
fig.update_xaxes(
    title="Time",
    tickformatstops=[
        # Very fine → seconds
        dict(dtickrange=[None, 1000], value="%H:%M:%S"),

        # Seconds to minutes
        dict(dtickrange=[1000, 60000], value="%H:%M:%S"),

        # Minutes
        dict(dtickrange=[60000, 3600000], value="%H:%M"),

        # Hours
        dict(dtickrange=[3600000, 86400000], value="%H:%M"),

        # Days+
        dict(dtickrange=[86400000, None], value="%d %b"),
    ]
)

# Dash server setup
port = 8051
url = f"http://127.0.0.1:{port}"

fig.show_dash(mode="external", port=port, open_browser=False)

# Open browser automatically
webbrowser.open(url)

  ```

  Tips:

  - Start by printing all dataset names and shapes before plotting.
  - Keep the same buffer-to-meaning mapping between controller versions.
  - If a buffer is missing, confirm it was assigned inside your control() function.
