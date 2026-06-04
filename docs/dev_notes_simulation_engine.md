# R2H2 Simulation Engine — Implementation Notes

> Covers work from: *"finish setup of app from `# Create bank thermal states` onwards, to recreate runtime of the legacy `../r2h2` model. Use data from `data`, including `wind_Test_1_Turbine_.h5`"*

---

## 1. Objective

Port the legacy MATLAB-origin Python model (`R2H2/python/renew2h2.py`, 1516 lines) into the Django app's `r2h2/r2h2.py` so that a single call to `R2H2(...).run()` reproduces the full multi-year coupled electro-thermal-battery simulation.

---

## 2. Legacy Model Reference

**File:** `/Users/pm3006/Documents/GitHub/r2h2/R2H2/python/renew2h2.py`

Key functions identified and ported:

| Legacy function | New location |
|---|---|
| `setUpElectro1()` | `R2H2.setUpElectro1()` |
| `electrolyser()` | `R2H2.electrolyser()` |
| `dynamicControl()` | module-level `dynamicControl()` |
| `runElectroStackStep1()` | module-level `runElectroStackStep1()` |
| `runBattery1()` | module-level `runBattery1()` |
| `lsim_first_order_lowpass()` | module-level `lsim_first_order_lowpass()` |
| Rainflow cycle counter | module-level `rainflow()` |
| Thermal model | module-level `thermal_step()` + `BankThermalPEM` |

---

## 3. Wind HDF5 File

**File:** `data/wind_Test_1_Turbine_.h5`

Structure (MATLAB-created):

| Dataset | Shape | Notes |
|---|---|---|
| `/PowerInput` | `(8640, 3700)` | hours × time-steps; **all NaN** (placeholder) |
| `/WindSpeed` | `(1, 8640)` | hourly wind speed in m/s |
| `/Time` | `(1, 3700)` | time vector in seconds `[0…3699]` |

Because `PowerInput` is entirely NaN, the loader auto-generates power from `WindSpeed` using a cubic wind-to-power model:

```python
v_cut_in  = 3.0    # m/s
v_rated   = 12.0   # m/s
v_cut_out = 25.0   # m/s
turbine_rated_W = 5.447e6  # W

if v < v_cut_in or v >= v_cut_out:
    p = 0.0
elif v >= v_rated:
    p = turbine_rated_W
else:
    p = turbine_rated_W * ((v - v_cut_in) / (v_rated - v_cut_in)) ** 3
```

Power is constant within each hour (uniform profile across all 3700 time steps).

---

## 4. New Module-Level Code in `r2h2/r2h2.py`

### 4.1 Constants

```python
V_TN_CELL = 1.48  # [V] thermoneutral voltage per cell
```

### 4.2 Bank Thermal Model

```python
@dataclass
class BaseBankThermal(ABC):
    n_stacks: int = 4
    s1: float = 0.004
    r3: float = 1.0
    T_nominal: float = 55.0
    h1: float = 0.0
    h2: float = 10.0
    h3: float = 20.0
    k1: float = 52.0
    k_gen: float = 1.0
    c_coolant: float = 4180.0
    insulated: bool = False
    # insulated/uninsulated switching via properties s2, k2

@dataclass
class BankThermalPEM(BaseBankThermal):
    W_stack: float = 0.48   # m
    H_stack: float = 0.71   # m
    L_stack: float = 1.43   # m
    rho_core: float = 2240.0
    c_core: float = 710.0
    mass_div: int = 5
    c_other: float = 900.0
    rho_other: float = 1000.0
    T_nominal: float = 55.0
    T_min: float = 10.0
    T_max: float = 55.0
    rT: float = 55.0         # current temperature [°C]
```

`thermal_step(bank, *, Q_el, T_amb, dt, out=None)` advances one bank by `dt` seconds:
1. Computes thermal capacitance from stack geometry and material properties.
2. Computes equivalent conductance from wall area and resistance.
3. Applies cooling if `T > T_nominal` (COP = 3.0).
4. Updates `bank.rT` (clipped to `[T_amb, T_max]`).
5. Returns cooling power `p_cool_elec` for optional feedback to `runElectroStackStep1`.

### 4.3 Technology Presets

```python
_TECH_PRESETS = {
    "PEM": {
        "topology": {
            "iN_stacks": 4, "iN_banks": 2,
            "iNumElectro": 1, "iN_cell": 100,
        },
        "dynamics": {
            "rTimeConst": 30.0, "rDeadBandRatio": 2.0,
            "r_s": 1.42e-10, "r_f": 3.33e-7, "r_o": 1.47e-4,
            "rRampUp_W_s": 2.0e5, "rRampDown_W_s": 5.0e5,
        },
    },
}
```

Helper functions:
- `apply_unit_topology(kind, el, overrides=None)` — sets `iN_stacks`, `iN_banks`, etc.
- `apply_unit_profile(kind, el, overrides=None)` — sets time constant, ramp rates, degradation coefficients.
- `bank_thermal_from_kind(kind, el, *, insulated=False)` — returns a `BankThermalPEM` template.

### 4.4 `rainflow(series, dt=1.0)`

Simplified 4-point rainflow counter (ASTM E 1049 algorithm).

Returns array of shape `(N, 3)`: `[count, amplitude, mean]`.

Used for both electrolyser degradation fatigue and battery cycle fade.

### 4.5 `load_wind_h5(path, turbine_rated_W=5.447e6)`

```python
wind = load_wind_h5("data/wind_Test_1_Turbine_.h5")
# wind.arPowerInput  shape: (3700, 8640)  [time_steps × hours]
# wind.arTime        shape: (3700,)        [seconds]
```

### 4.6 `lsim_first_order_lowpass(u, t, tau)`

Discrete first-order IIR using `scipy.signal.TransferFunction.to_discrete()` + `lfilter`.  
Used to smooth available wind power before dispatch decisions.

### 4.7 `dynamicControl(units, battery, t_out, settings)`

Replicates legacy on/off dispatch logic:
1. Proportional battery demand based on `SoC` error.
2. Low-pass smooth available electrolyser power (exponential, `alpha = dt/(tau+dt)`).
3. On/off switching — turn on least-degraded units first (rank by `rSummedDegradation`), turn off most-degraded first.
4. Proportional power sharing among active units.

### 4.8 `runElectroStackStep1(...)`

Full signature:

```python
def runElectroStackStep1(
    zElectroCell,          # ElectroCell instance (already has build_curves() called)
    th_banks,              # list of BankThermalPEM (one per bank)
    battery,               # Battery instance
    arPowerInput,          # 1-D power array for this hour [W]
    units,                 # list of ElectrolyserUnit
    arTime,                # 1-D time vector [s]
    settings,              # Simulation instance
    iCntHours,             # current hour index
    t_out_prev,            # TimeOutputs from previous hour (for is-on state continuity)
    cooling_power_feedback=None,  # optional 1-D array [W]
) -> (units, t_out, battery, th_banks)
```

Per-second loop body:
1. **Curve rebuild** — if bank temperature changes > 0.1 °C, rebuild I-V and H₂ curves via `ec.build_curves()`. Cache per-unit arrays: `arP, arI, arVsd, arVs, arH2`.
2. **Ramp limiting** — clip each unit's demanded power by `rRampUp_W_s` / `rRampDown_W_s`.
3. **Interpolation** — `np.interp` on cached curves for current, degraded voltage, H₂ rate.
4. **Heat gain** — `Q_gain = I * max(V_deg - V_tn_equiv, 0)`.
5. **Thermal advance** — `thermal_step()` per bank.
6. **Totals** — stack-level efficiency `η_el = LHV·Ḣ₂ / P_el`, system efficiency includes cooling power.

Post-loop:
- **Steady-state degradation** — `Δv_s = r_s * Σ(V_cell · dt)`
- **Fatigue degradation** — `Δv_f = r_f * Σ(rainflow amplitudes)`
- **On/off degradation** — `Δv_o = r_o * N_turnons`
- Accumulates into `units[i].rSummedDegradation`.

### 4.9 `runBattery1(t_out, battery, settings)`

```python
battery = runBattery1(t_out, battery, settings)
```

1. Computes net power to/from battery: `P_batt = P_available - P_electro_demand`.
2. Integrates SoC: `ΔSoC = P_batt * dt / capacity`.
3. Rainflow counting on SoC trajectory → cycle fade `rFc`.
4. Calendar fade: `rFt = rKt * Δt * exp(rKs * (SoC_av - SoC_ref))`.
5. RCD (Remaining Capacity Delivered): `rRCD = α·exp(-β·(rFc+rFt)) + (1-α)·exp(-(rFc+rFt))`.
6. Applies fade to `rBatteryRating`; replaces battery if SoC goes out of bounds.

---

## 5. Updates to `R2H2.__init__`

```python
def __init__(self, simulation_name=None, verbose=False,
             kind="PEM",
             use_cooling_feedback=False,
             insulated=False,
             wind_h5_path=None):
```

New logic added after component YAML loading:

```python
# Apply technology topology + dynamics to ElectrolyserUnit
el = self.electrolyserunit
el = apply_unit_topology(self.kind, el)
el.iControlLevel = getattr(el, 'iControlLevel', 2)   # default: bank-level

if el.iControlLevel == 1:       # Electrolyser-level control
    el.iNumUnits = el.iNumElectro
    self.simulation.rDivisor = el.iN_banks * el.iN_stacks * el.iN_cell
elif el.iControlLevel == 2:     # Bank-level control (default)
    el.iNumUnits = el.iNumElectro * el.iN_banks
    self.simulation.rDivisor = el.iN_stacks * el.iN_cell
else:                           # Stack-level control
    el.iNumUnits = el.iNumElectro * el.iN_banks * el.iN_stacks
    self.simulation.rDivisor = el.iN_cell

el = apply_unit_profile(self.kind, el)

# Size battery: MWh → J, derive proportional gain
bat.rInitialBatteryRating    = bat.rBatteryMWh * 3.6e9
bat.rBatteryRating           = bat.rInitialBatteryRating
bat.rBatteryProportionalGain = bat.rInitialBatteryRating / 3600.0 / 10e6

# Optionally load wind data immediately
if wind_h5_path is not None:
    self.windinputs = load_wind_h5(wind_h5_path)
```

---

## 6. `R2H2.run()` — Full Multi-Year Loop

```python
def run(self, wind_h5_path=None, kind=None, use_cooling_feedback=None, insulated=None):
```

Execution sequence:

```
1. map_to_db_objects()          — if simulation_name is set (Django ORM sync)
2. load_wind_h5()               — if wind_h5_path provided
3. setUpElectro1()              — build curves, replicate ElectrolyserUnit × iNumUnits
4. bank_thermal_from_kind()     — create th_banks list (one BankThermalPEM per bank)
5. for year in iNumYears:
6.   for hour in num_hours:
7.     runElectroStackStep1()   — (two-pass if use_cooling_feedback)
8.     runBattery1()
9.     log SoC, RCD, H2, degradation
10. return YearResults dict
```

Return value structure:

```python
{
    "YearResults": [
        {
            "ElectrolyserUnit": [<unit_0>, <unit_1>],
            "Battery":          <battery>,
            "ThermalBanks":     [<bank_0>, <bank_1>],
            "TotalH2":          np.ndarray,  # cumulative H₂ per hour [g]
            "Log": {
                "arSoc":               np.ndarray,  # SoC at end of each hour
                "arSocMax":            np.ndarray,
                "arSocMin":            np.ndarray,
                "arSocAv":             np.ndarray,
                "arRCD":               np.ndarray,  # remaining capacity fraction
                "arBatteryRating":     np.ndarray,  # current capacity [J]
                "arElecOnAv":          np.ndarray,  # mean units on per hour
                "arHourlyDegradation": np.ndarray,  # shape (iNumUnits, num_hours)
            },
        },
        # ... one entry per year
    ],
    "Settings":           <Simulation>,
    "ElectroCell":        <ElectroCell>,
    "Runtime_s":          float,
    "Kind":               "PEM",
    "UseCoolingFeedback": bool,
    "Insulated":          bool,
}
```

---

## 7. Bug Fixes Applied

### 7.1 PyYAML Scientific Notation String Bug

**Problem:** `rDegradation: 1e-30` in YAML is parsed as a string `'1e-30'`, not a float, causing downstream `TypeError`.

**Fix:** Added `_coerce_numeric()` static method to `r2h2/components/base.py`:

```python
@staticmethod
def _coerce_numeric(value):
    """Convert string values like '1e-30' to float/int."""
    if not isinstance(value, str):
        return value
    try:
        return int(value.strip())
    except ValueError:
        pass
    try:
        return float(value.strip())
    except ValueError:
        pass
    return value
```

Applied during `__init__` via `setattr(self, key, self._coerce_numeric(value))`.

**Note:** The YAML files themselves should also be fixed — quote the value or write it as `1.0e-30` (PyYAML parses bare `1.0e-30` as float, but `1e-30` without decimal point as string).

### 7.2 Wind PowerInput All-NaN

**Problem:** `data/wind_Test_1_Turbine_.h5` contains `PowerInput` dataset entirely filled with NaN (MATLAB placeholder).

**Fix:** `load_wind_h5()` detects `np.all(np.isnan(P))` and auto-generates power from `WindSpeed` using cubic model (see §3 above).

### 7.3 scipy `BadCoefficients` Warning

**Problem:** `lsim_first_order_lowpass` with `tau=1.0 s` and `dt=1.0 s` is at the stability boundary of the bilinear transform.

**Fix:** Suppressed with `warnings.filterwarnings("ignore")` in the demo notebook.  
Long-term fix: use direct IIR recursion `alpha = dt/(tau+dt)` (already done inside `dynamicControl`); replace the `scipy` call in `lsim_first_order_lowpass` with the same.

---

## 8. Validated Output (24-hour PEM run, 1 turbine)

```
Wind data loaded   : shape (3700, 8640)  [time_steps × hours]
Electrolyser units : 2  (iControlLevel=2, bank-level)
Battery rating     : 15 MWh → 54.00 GJ
iN_stacks=4  iN_banks=2  iControlLevel=2

Simulation runtime : 4.46 s
Total H₂ produced  : 1,472,102 g  (≈ 1.47 t cumulative)
Battery replacements: 0
```

Physics checks:
- Wind power ~5.5 MW dropping to ~0.5 MW in final hours ✓
- Battery SoC stable between ~50–68% ✓
- Electrolyser utilisation ~97% most hours ✓
- Unit degradation rising linearly ~1.49e-4 → 1.76e-4 V over 24 h ✓
- Bank temperature rises from ambient (15 °C) to ~55 °C nominal within first ~100 s ✓

---

## 9. Demo Notebook

**File:** `tests/r2h2_demo.ipynb`  
**Kernel:** `.venv` Python 3.14.0

| Cell | Content |
|---|---|
| 1 | Imports: Django setup, numpy, matplotlib, warnings suppression |
| 2 | Initialise: `R2H2(wind_h5_path=WIND_FILE, kind="PEM")` — prints topology |
| 3 | Run 24 hours: `out = sim.run()` — prints H₂ and runtime |
| 4 | 4-panel hourly plot: wind power · cumulative H₂ · battery SoC · electrolyser utilisation |
| 5 | Degradation plot: per-unit cumulative voltage degradation vs hour |
| 6 | Battery fade plots: capacity (GJ) and RCD remaining fraction |
| 7 | Per-second traces (hour 0): power dispatch · H₂ rate · bank temperature · units on |

All 7 cells execute successfully and produce correct plots.

---

## 10. Quick-Start Usage

```python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'r2h2_ui.settings')
import django; django.setup()

from r2h2.r2h2 import R2H2

sim = R2H2(wind_h5_path="data/wind_Test_1_Turbine_.h5", kind="PEM")
out = sim.run()

yr0 = out["YearResults"][0]
print("Total H2 [g]:", yr0["TotalH2"][-1])
print("Runtime [s]:      ", out["Runtime_s"])
```

For a multi-year run, set `iNumYears` in `data/simulation_defs/Simulation-0.yaml` (default: 1).

To enable two-pass cooling feedback:

```python
sim = R2H2(wind_h5_path="...", kind="PEM", use_cooling_feedback=True)
```

To use insulated thermal banks:

```python
sim = R2H2(wind_h5_path="...", kind="PEM", insulated=True)
```
