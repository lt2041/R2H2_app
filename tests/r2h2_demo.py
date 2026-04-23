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
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

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
print(f"Total H2 produced  : {yr0['TotalH2'][-1]:.0f} g/s·s  "
      f"({yr0['TotalH2'][-1]/1e6:.3f} kg·s)")
print(f"Battery replacements: {yr0['Battery'].iNumReplacements}")

# %% [markdown]
# ## 3 – Results

# %%
hours = np.arange(N_HOURS)

# ── Wind power input (hour-average) ─────────────────────────────────────
P_wind_avg = sim.windinputs.arPowerInput.mean(axis=0)   # W, one value per hour

fig, axes = plt.subplots(4, 1, figsize=(12, 14), sharex=True)
fig.suptitle("R2H2 Simulation – 24-hour demo (PEM, 1 turbine)", fontsize=14)

# ── Wind power ───────────────────────────────────────────────────────────
axes[0].plot(hours, P_wind_avg / 1e6, color="steelblue", linewidth=1.5)
axes[0].set_ylabel("Wind power\n[MW]")
axes[0].grid(True, alpha=0.4)
axes[0].set_title("Available wind power")

# ── Cumulative H2 production ─────────────────────────────────────────────
axes[1].plot(hours, yr0["TotalH2"] / 1e6, color="forestgreen", linewidth=1.5)
axes[1].set_ylabel("Cumulative H₂\n[kg·s]")
axes[1].grid(True, alpha=0.4)
axes[1].set_title("Cumulative hydrogen production")

# ── Battery SoC ──────────────────────────────────────────────────────────
axes[2].plot(hours, log["arSoc"] * 100, color="darkorange", linewidth=1.5)
axes[2].axhline(50, color="gray", linestyle="--", linewidth=0.8, label="SoC ref 50%")
axes[2].set_ylabel("Battery SoC [%]")
axes[2].set_ylim(0, 100)
axes[2].legend(fontsize=8)
axes[2].grid(True, alpha=0.4)
axes[2].set_title("Battery state of charge")

# ── Electrolyser utilisation ─────────────────────────────────────────────
num_units = sim.electrolyserunit.iNumUnits
axes[3].bar(hours, log["arElecOnAv"] / num_units * 100,
            color="mediumpurple", alpha=0.8, width=0.8)
axes[3].set_ylabel("Units on [%]")
axes[3].set_ylim(0, 105)
axes[3].set_xlabel("Hour")
axes[3].grid(True, alpha=0.4, axis="y")
axes[3].set_title(f"Electrolyser utilisation (max {num_units} units)")

plt.tight_layout()
plt.show()

# %% [markdown]
# ## 4 – Hourly degradation

# %%
deg = log["arHourlyDegradation"]   # shape: (num_units, num_hours)

fig, ax = plt.subplots(figsize=(12, 4))
for i in range(deg.shape[0]):
    ax.plot(hours, deg[i, :], label=f"Unit {i+1}", linewidth=1.5)
ax.set_xlabel("Hour")
ax.set_ylabel("Cumulative degradation [V]")
ax.set_title("Electrolyser unit degradation (summed)")
ax.legend()
ax.grid(True, alpha=0.4)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 5 – Battery capacity fade

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

axes[0].plot(hours, log["arBatteryRating"] / 1e9, color="darkorange", linewidth=1.5)
axes[0].set_xlabel("Hour")
axes[0].set_ylabel("Battery rating [GJ]")
axes[0].set_title("Battery capacity (GJ)")
axes[0].grid(True, alpha=0.4)

axes[1].plot(hours, log["arRCD"], color="tomato", linewidth=1.5)
axes[1].set_xlabel("Hour")
axes[1].set_ylabel("RCD (remaining capacity)")
axes[1].set_title("Remaining capacity fraction")
axes[1].set_ylim(0.9, 1.01)
axes[1].grid(True, alpha=0.4)

plt.suptitle("Battery degradation", fontsize=13)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 6 – Per-second traces (first hour)

# %%
# Re-run just hour 0 and keep the t_out object for second-resolution traces
from r2h2.r2h2 import runElectroStackStep1, bank_thermal_from_kind
import copy

sim2 = R2H2(wind_h5_path=WIND_FILE, kind="PEM", verbose=False)
sim2.windinputs.arPowerInput = sim2.windinputs.arPowerInput[:, :1]
sim2.setUpElectro1()

el      = sim2.electrolyserunit
n_banks = el.iN_banks * el.iNumElectro
th_tmpl = bank_thermal_from_kind("PEM", el)
th_banks = [copy.deepcopy(th_tmpl) for _ in range(n_banks)]

units, t_out, _, th_banks = runElectroStackStep1(
    sim2.electrocellpem,
    th_banks,
    sim2.battery,
    sim2.windinputs.arPowerInput[:, 0],
    sim2.electrolyserunits,
    sim2.windinputs.arTime,
    sim2.simulation,
    0,
    None,
)

t = sim2.windinputs.arTime

fig, axes = plt.subplots(4, 1, figsize=(12, 14), sharex=True)
fig.suptitle("Per-second traces – hour 0", fontsize=14)

axes[0].plot(t, t_out.arAvailablePower / 1e6, label="Available", color="steelblue")
axes[0].plot(t, t_out.arP_el_total / 1e6, label="Electrolyser demand", color="tomato")
axes[0].set_ylabel("Power [MW]")
axes[0].legend(fontsize=8)
axes[0].grid(True, alpha=0.4)
axes[0].set_title("Power dispatch")

axes[1].plot(t, t_out.arH2Dot_total * 1e3, color="forestgreen")
axes[1].set_ylabel("H₂ rate [mg/s]")
axes[1].grid(True, alpha=0.4)
axes[1].set_title("Instantaneous H₂ production rate")

axes[2].plot(t, t_out.arT_stack, color="darkorange")
axes[2].set_ylabel("Bank temp [°C]")
axes[2].grid(True, alpha=0.4)
axes[2].set_title("Mean bank temperature")

axes[3].plot(t, t_out.arTotalElectroOn, color="mediumpurple")
axes[3].set_ylabel("Units on")
axes[3].set_xlabel("Time [s]")
axes[3].set_ylim(-0.1, sim2.electrolyserunit.iNumUnits + 0.5)
axes[3].grid(True, alpha=0.4)
axes[3].set_title("Active electrolyser units")

plt.tight_layout()
plt.show()


