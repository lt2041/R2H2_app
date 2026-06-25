# Dynamic Controller User Guide

## Overview

R2H2 supports two controller modes:

- Built-in controller: `dynamicControl`
- Custom controller: user-provided Python function named `control`

The controller is executed once per simulation hour and generates per-second dispatch arrays for that hour.

If a custom controller is configured, R2H2 loads it at run start and calls `control` each hour. If loading, execution, or validation fails, R2H2 automatically falls back to built-in `dynamicControl`.

### Key Outputs
The controller MUST provide the outputs:
  - `t_out.arTotalElectroDemand`
  - `t_out.aiIsOn`
  - `t_out.arProportionPower`

They must have the shape 
  - `len(arTotalElectroDemand) == T`
  - `shape(aiIsOn) == (num_units, T)`
  - `shape(arProportionPower) == (num_units, T)`

Where num_units is the number of electrolyser units in the simulation (default is 10 units) and T is the total seconds in one hour (3600) PLUS 100 transient seconds. These transient seconds are disregarded in the simulation.


## Custom Controller Function 

Your controller file must define:

```python
def control(units, battery, t_out, settings):
    # update units, battery, t_out
    return units, t_out, battery
```

### Inputs

Your function receives:

1. `units`
- List of electrolyser unit objects.
- Commonly used fields:
  - `rSummedDegradation`
  - `rMinPower_s`
  - `rRatedPower_s`
  - `rDeadBandRatio`
  - `rTotalTurnOns`

2. `battery`
- Battery state and control parameters.
- Common fields:
  - `arInitialSoC`
  - `rControlTargetSoC`
  - `rBatteryProportionalGain`
  - `rBatteryRating`
  - `arBatteryDemand` (optional from custom controller)

3. `t_out`
- Hourly per-second output container, pre-initialized before controller call.
- Required outputs:
  - `arTotalElectroDemand`
  - `aiIsOn`
  - `arProportionPower`
- Optional outputs:
  - `arTotalElectroOn`
  - `arElectroAvailablePowerA`
  - `arElectroAvailablePower`
  - `arBuffer1` .. `arBuffer20`

4. `settings`
- Simulation settings.
- Common fields:
  - `rTimeStep`
  - `rTransientSteps`

### Return Value

Return exactly a 3-tuple:

- `units`
- `t_out`
- `battery`

## Validation and Fallback Behavior

- There is a 30 s wall-clock timeout per hourly call.
- Exception-safe execution with fallback.
- The following required outputs must exist:
  - `t_out.arTotalElectroDemand`
  - `t_out.aiIsOn`
  - `t_out.arProportionPower`
- They shoud have the right shapes. Shape checks:
  - `len(arTotalElectroDemand) == T`
  - `shape(aiIsOn) == (num_units, T)`
  - `shape(arProportionPower) == (num_units, T)`
- NaN/Inf guard on required arrays.

If validation fails for any reason, R2H2 emits a warning and falls back to `dynamicControl` for that hour.

## Built-In Controller Behavior (`dynamicControl`)

The built-in controller:

- Seeds `aiIsOn` from the previous final state.
- Uses a battery SoC proportional regulator toward `rControlTargetSoC`.
- Applies battery rate limits and SoC floor protection.
- Computes:
  - `arElectroAvailablePowerA = max(arAvailablePower - arBatteryDemand, 0)`
- Applies first-order smoothing to get `arElectroAvailablePower`.
- Decides ON/OFF count from available power and unit min/rated limits.
- Fills `arProportionPower` uniformly across ON units.
- Produces `arTotalElectroDemand` clipped to fleet min/max.

If you want to disable built-in SoC correction behavior, set:

- `battery.rBatteryProportionalGain = 0`

## Post-Controller Physical Guards (Applied To All Controllers)

After controller return, R2H2 applies additional execution guards in `runElectroStackStep1`:

- Non-binary `aiIsOn` entries are treated as invalid and replaced with `0`.
  - Per-second invalid-count is recorded in `t_out.aiAssignmentError`.
  - Cleaned ON matrix is stored in `t_out.aiIsOn_clean`.
- Total ON count is recomputed from cleaned `aiIsOn`.
- Total demand is clipped to:
  - lower bound: `min_power * arTotalElectroOn`
  - upper bound: `rated_power * arTotalElectroOn`
- Effective `rated_power` uses `max(curve_rated, nominal_nameplate_if_available)`.
- If too many units are ON to satisfy per-unit minimum power, low-priority units are switched OFF.
- Remaining demand is reallocated across ON units with bounded allocation.
- Per-unit ramp-rate and min/max bounds are enforced in the per-second loop.

This means controller outputs are treated as requested dispatch and may be adjusted to satisfy physical feasibility.

## Power and Battery Consistency Notes

- Inside electro-thermal execution, `t_out.arElectroDemand` is per-unit executed demand.
- End-of-hour, `t_out.arTotalElectroDemand` is set to:
  - `sum(arElectroDemand, axis=0) + ancillary_power`
- Battery step uses:
  - `P_batt = arAvailablePower - arTotalElectroDemand`

So battery dynamics use post-guard, executed plant demand (including ancillary load), not raw pre-guard controller request.

## Minimal Custom Controller Example

```python
import numpy as np


def control(units, battery, t_out, settings):
    T = len(t_out.arAvailablePower)
    n_units = len(units)

    # Required output 1: total fleet demand [W], length T
    t_out.arTotalElectroDemand = np.asarray(t_out.arAvailablePower, dtype=float).copy()

    # Required output 2: ON/OFF matrix, shape (n_units, T)
    t_out.aiIsOn[:, :] = 0
    step0 = int(settings.rTransientSteps)
    step0 = max(1, min(step0, T - 1))
    t_out.aiIsOn[:, step0:] = 1

    # Required output 3: per-unit proportions, shape (n_units, T)
    t_out.arProportionPower[:, :] = 0.0
    on_count = np.sum(t_out.aiIsOn, axis=0).astype(float)
    on_mask = on_count > 0
    if np.any(on_mask):
        t_out.arProportionPower[:, on_mask] = (
            t_out.aiIsOn[:, on_mask] / on_count[on_mask]
        )

    return units, t_out, battery
```

## Custom Controller Loading

At run start, R2H2 loads the selected controller module and reads:

- `control` callable (required)
- `end_hour_buffer_map` or `END_HOUR_BUFFER_MAP` (optional)

If `end_hour_buffer_map` exists but is not a `dict`, it is ignored.

## 1 Hz Collection Model (Current Behavior)

When 1 Hz collection is enabled, R2H2 collects only variables listed in `Simulation.hz_variables`.

Important current behavior:

- If `hz_variables` is empty, no 1 Hz channel datasets are produced.
- `time_indices` is always sequential across collected hours.
- Only successfully resolved and shape-compatible variables are stored.
- If no selected channels produce data, `TimeSeriesOutput` is omitted.

### Variable Resolution Order

For each selected variable name:

1. If it matches a controller alias from `buffer = {...}` mapping, resolve from:
   - `battery.<attr>` or
   - `t_out.<attr>`
2. Otherwise resolve from `t_out.<selected_name>` directly.

### Accepted Shapes for Selected Variables

Per selected variable during hourly collection:

- Scalar: broadcast to that hour's trimmed 1 Hz length.
- 1-D array of full hourly axis length `T`: transient-trimmed.
- 1-D array of trimmed length `n_hz`: used directly.
- 1-D array of length `n_hz + 1`: first sample dropped (battery-style arrays).
- 1-D array of length `1`: broadcast.

Skipped:

- Non-1-D arrays.
- 1-D arrays with unsupported lengths.

## `buffer = {...}` Alias Map for 1 Hz Selection

R2H2 parses controller source for a top-level variable named `buffer`:

```python
buffer = {
    "soc": battery.arSoC,
    "total_on": t_out.arTotalElectroOn,
}
```

If you add alias keys there, those keys can be selected in `hz_variables` and resolved at runtime.

Notes:

- Parser accepts assignments to `buffer` in `Assign` or `AnnAssign` forms.
- Alias values must be attribute references on `battery` or `t_out`.

## End-Of-Hour Buffer Mapping (`arBuffer1`..`arBuffer20`)

Optional in controller module:

```python
end_hour_buffer_map = {
    "arBuffer1": "arEta_system_total",
    "arBuffer2": "arT_stack",
    "arBuffer3": lambda t: np.mean(t.arTotalElectroOn),
}
```

Behavior:

- Applied after hourly post-processing, including `runBattery1`.
- Also exposes `t_out.arBatterySoC` (end-of-hour value) before mapping.
- Mapping values may be:
  - `str`: attribute name on `t_out`
  - `callable`: `fn(t_out)`
  - scalar/array-like: last element used
- Each mapped value must resolve to a finite scalar.
- Mapping only affects 1 Hz output if that buffer name is selected in `hz_variables`.
- Mapping fills the collected hour segment with the resolved scalar value.

## Recommended Workflow

1. Start from minimal required outputs.
2. Validate shape and finite numeric values every hour.
3. Run short windows first.
4. Add optional `buffer` aliases and/or `end_hour_buffer_map` only as needed.
5. Select only the 1 Hz variables you need to limit output size.
6. Scale duration after behavior is stable.

## Troubleshooting

Symptom: custom controller appears ignored.

Common causes:

- Missing `control` function.
- Wrong return tuple format.
- Shape mismatch in required arrays.
- NaN/Inf in required arrays.
- Runtime exception in controller.
- 30 s timeout in controller call.

Checks:

1. `control(units, battery, t_out, settings)` exists.
2. Return is exactly `(units, t_out, battery)`.
3. Required arrays have correct dimensions.
4. Required arrays are finite.
5. If collecting 1 Hz channels, ensure selected variable names exist and are 1-D compatible.
