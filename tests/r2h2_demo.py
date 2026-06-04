# %%
import sys, os
from pathlib import Path

# ── Ensure the project root is on sys.path ──────────────────────────────
PROJECT_ROOT = Path("../").resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Django setup (needed for Paths() to resolve data_root) ──────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "r2h2_ui.settings")
import django
django.setup()

import numpy as np
import warnings
warnings.filterwarnings("ignore")

from r2h2.plots import (
    plot_hourly_overview,
    plot_degradation,
    plot_battery_fade,
    plot_second_traces,
    plot_bank_temperatures,
    plot_all,
)

print("Imports OK")


# %% [markdown]
# ## 1 – Initialise simulation

# %%
from r2h2.r2h2 import R2H2

WIND_FILE = str(PROJECT_ROOT / "data" / "wind_Test_1_Turbine_.h5")

sim = R2H2(
    wind_h5_path=WIND_FILE,
    kind="PEM",
    use_cooling_feedback=False,
    insulated=False,
    verbose=False,
)

print(f"Wind data loaded  : {sim.windinputs.arPowerInput.shape}  (time_steps × hours)")
print(f"Electrolyser units: {sim.electrolyserunit.iNumUnits}")
print(f"Battery rating    : {sim.battery.rBatteryMWh} MWh  "
      f"→ {sim.battery.rInitialBatteryRating/1e9:.2f} GJ")
print(f"iN_stacks={sim.electrolyserunit.iN_stacks}  "
      f"iN_banks={sim.electrolyserunit.iN_banks}  "
      f"iControlLevel={sim.electrolyserunit.iControlLevel}")

# %% [markdown]
# ## 2 – Run (first 24 hours)

# %%
N_HOURS = 24
sim.windinputs.arPowerInput = sim.windinputs.arPowerInput[:, :N_HOURS]

out  = sim.run()
yr0  = out["YearResults"][0]
log  = yr0["Log"]

print(f"Simulation runtime : {out['Runtime_s']:.2f} s")
print(f"Total H2 produced  : {yr0['TotalH2'][-1]:.0f} g  "
      f"({yr0['TotalH2'][-1]/1e3:.3f} kg)")
print(f"Battery replacements: {yr0['Battery'].iNumReplacements}")

# %% [markdown]
# ## 3 – Results

# %%
# backend="plotly" is the default — pass backend="matplotlib" for static output
plot_hourly_overview(sim, out, backend="plotly")


# %% [markdown]
# ## 4 – Hourly degradation

# %%
plot_degradation(out, backend="plotly")


# %% [markdown]
# ## 5 – Battery capacity fade

# %%
plot_battery_fade(out, backend="plotly")


# %% [markdown]
# ## 6 – Per-second traces (first hour)

# %%
fig, _ = plot_second_traces(sim, hour=0, backend="plotly")
fig



