#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
r2h2.plots
==========
Standard results plots for an R2H2 simulation run.

Usage
-----
    from r2h2.plots import plot_hourly_overview, plot_degradation,
                            plot_battery_fade, plot_second_traces, plot_all

    out  = sim.run()
    figs = plot_all(sim, out)          # returns dict of Figure objects

    # Or call individually:
    fig = plot_hourly_overview(sim, out)
    fig = plot_degradation(out)
    fig = plot_battery_fade(out)
    fig, t_out = plot_second_traces(sim, hour=0)

All functions accept an optional ``save_path`` keyword argument.  When
supplied, the figure is saved to that path before being returned.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Optional, Union

import numpy as np

# ---------------------------------------------------------------------------
# Lazy matplotlib import — avoids hard dependency at module load time
# ---------------------------------------------------------------------------

def _plt():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError as exc:
        raise ImportError(
            "matplotlib is required for plotting.  Install it with:  pip install matplotlib"
        ) from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _maybe_save(fig, save_path: Optional[Union[str, Path]]) -> None:
    if save_path is not None:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")


def _year0_log(out: dict) -> dict:
    return out["YearResults"][0]["Log"]


# ---------------------------------------------------------------------------
# 1.  Hourly overview (4-panel)
# ---------------------------------------------------------------------------

def plot_hourly_overview(
    sim,
    out: dict,
    year: int = 0,
    title: Optional[str] = None,
    save_path: Optional[Union[str, Path]] = None,
):
    """Four-panel hourly overview plot.

    Panels
    ------
    1. Available wind power [MW]
    2. Cumulative H₂ production [kg·s]
    3. Battery state of charge [%]
    4. Electrolyser utilisation [%]

    Parameters
    ----------
    sim:
        An :class:`R2H2` instance (used for ``windinputs`` and ``electrolyserunit``).
    out:
        Return value of :py:meth:`R2H2.run`.
    year:
        Year index to plot (default: 0).
    title:
        Figure suptitle.  Defaults to a sensible description.
    save_path:
        If provided, the figure is saved to this path.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _plt()

    log      = out["YearResults"][year]["Log"]
    total_h2 = out["YearResults"][year]["TotalH2"]
    num_hours = len(log["arSoc"])
    hours     = np.arange(num_hours)
    num_units = sim.electrolyserunit.iNumUnits

    P_wind_avg = sim.windinputs.arPowerInput.mean(axis=0)[:num_hours]

    fig, axes = plt.subplots(4, 1, figsize=(12, 14), sharex=True)
    fig.suptitle(
        title or f"R2H2 Simulation – hourly overview (year {year + 1})",
        fontsize=14,
    )

    # Wind power
    axes[0].plot(hours, P_wind_avg / 1e6, color="steelblue", linewidth=1.5)
    axes[0].set_ylabel("Wind power\n[MW]")
    axes[0].grid(True, alpha=0.4)
    axes[0].set_title("Available wind power")

    # Cumulative H2
    axes[1].plot(hours, total_h2 / 1e6, color="forestgreen", linewidth=1.5)
    axes[1].set_ylabel("Cumulative H₂\n[kg·s]")
    axes[1].grid(True, alpha=0.4)
    axes[1].set_title("Cumulative hydrogen production")

    # Battery SoC
    axes[2].plot(hours, log["arSoc"] * 100, color="darkorange", linewidth=1.5)
    axes[2].axhline(50, color="gray", linestyle="--", linewidth=0.8, label="SoC ref 50 %")
    axes[2].set_ylabel("Battery SoC [%]")
    axes[2].set_ylim(0, 100)
    axes[2].legend(fontsize=8)
    axes[2].grid(True, alpha=0.4)
    axes[2].set_title("Battery state of charge")

    # Electrolyser utilisation
    axes[3].bar(
        hours,
        log["arElecOnAv"] / num_units * 100,
        color="mediumpurple", alpha=0.8, width=0.8,
    )
    axes[3].set_ylabel("Units on [%]")
    axes[3].set_ylim(0, 105)
    axes[3].set_xlabel("Hour")
    axes[3].grid(True, alpha=0.4, axis="y")
    axes[3].set_title(f"Electrolyser utilisation (max {num_units} units)")

    plt.tight_layout()
    _maybe_save(fig, save_path)
    return fig


# ---------------------------------------------------------------------------
# 2.  Hourly degradation per unit
# ---------------------------------------------------------------------------

def plot_degradation(
    out: dict,
    year: int = 0,
    title: Optional[str] = None,
    save_path: Optional[Union[str, Path]] = None,
):
    """Cumulative per-unit electrolyser degradation vs hour.

    Parameters
    ----------
    out:
        Return value of :py:meth:`R2H2.run`.
    year:
        Year index to plot (default: 0).
    title:
        Axis title override.
    save_path:
        If provided, the figure is saved to this path.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _plt()

    log = _year0_log(out) if year == 0 else out["YearResults"][year]["Log"]
    deg = log["arHourlyDegradation"]   # shape: (num_units, num_hours)
    hours = np.arange(deg.shape[1])

    fig, ax = plt.subplots(figsize=(12, 4))
    for i in range(deg.shape[0]):
        ax.plot(hours, deg[i, :], label=f"Unit {i + 1}", linewidth=1.5)
    ax.set_xlabel("Hour")
    ax.set_ylabel("Cumulative degradation [V]")
    ax.set_title(title or "Electrolyser unit degradation (summed, per unit)")
    ax.legend()
    ax.grid(True, alpha=0.4)
    plt.tight_layout()
    _maybe_save(fig, save_path)
    return fig


# ---------------------------------------------------------------------------
# 3.  Battery capacity fade
# ---------------------------------------------------------------------------

def plot_battery_fade(
    out: dict,
    year: int = 0,
    title: Optional[str] = None,
    save_path: Optional[Union[str, Path]] = None,
):
    """Two-panel battery capacity fade plot.

    Left panel : battery rating [GJ] vs hour.
    Right panel: RCD (remaining capacity fraction) vs hour.

    Parameters
    ----------
    out:
        Return value of :py:meth:`R2H2.run`.
    year:
        Year index to plot (default: 0).
    title:
        Figure suptitle override.
    save_path:
        If provided, the figure is saved to this path.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _plt()

    log   = out["YearResults"][year]["Log"]
    hours = np.arange(len(log["arSoc"]))

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
    axes[1].set_ylim(
        max(0.0, float(np.min(log["arRCD"])) - 0.01),
        min(1.0, float(np.max(log["arRCD"])) + 0.01),
    )
    axes[1].grid(True, alpha=0.4)

    fig.suptitle(title or "Battery degradation", fontsize=13)
    plt.tight_layout()
    _maybe_save(fig, save_path)
    return fig


# ---------------------------------------------------------------------------
# 4.  Per-second traces for a single hour
# ---------------------------------------------------------------------------

def plot_second_traces(
    sim,
    hour: int = 0,
    title: Optional[str] = None,
    save_path: Optional[Union[str, Path]] = None,
):
    """Four-panel per-second resolution traces for one simulation hour.

    The function re-runs ``runElectroStackStep1`` for the requested hour from
    a fresh :class:`R2H2` state (i.e. no accumulated degradation).

    Panels
    ------
    1. Power dispatch: available vs electrolyser demand [MW]
    2. Instantaneous H₂ production rate [mg/s]
    3. Mean bank temperature [°C]
    4. Active electrolyser units count

    Parameters
    ----------
    sim:
        An :class:`R2H2` instance.  ``setUpElectro1()`` will be called
        internally on a deep copy — the original object is not modified.
    hour:
        Hour index to plot (0-based, default: 0).
    title:
        Figure suptitle override.
    save_path:
        If provided, the figure is saved to this path.

    Returns
    -------
    (fig, t_out) : tuple
        The figure and the :class:`TimeOutputs` object from the run.
    """
    plt = _plt()

    from r2h2.r2h2 import runElectroStackStep1, bank_thermal_from_kind

    sim2 = copy.deepcopy(sim)
    sim2.setUpElectro1()

    el      = sim2.electrolyserunit
    n_banks = el.iN_banks * el.iNumElectro
    th_tmpl = bank_thermal_from_kind(sim2.kind, el, insulated=sim2.insulated)
    th_banks = [copy.deepcopy(th_tmpl) for _ in range(n_banks)]

    P_hour = sim2.windinputs.arPowerInput[:, hour]

    units, t_out, _, _ = runElectroStackStep1(
        sim2.electrocellpem,
        th_banks,
        sim2.battery,
        P_hour,
        sim2.electrolyserunits,
        sim2.windinputs.arTime,
        sim2.simulation,
        hour,
        None,
    )

    t = sim2.windinputs.arTime

    fig, axes = plt.subplots(4, 1, figsize=(12, 14), sharex=True)
    fig.suptitle(title or f"Per-second traces – hour {hour}", fontsize=14)

    # Power dispatch
    axes[0].plot(t, t_out.arAvailablePower / 1e6, label="Available", color="steelblue")
    axes[0].plot(t, t_out.arP_el_total / 1e6,     label="Electrolyser demand", color="tomato")
    axes[0].set_ylabel("Power [MW]")
    axes[0].legend(fontsize=8)
    axes[0].grid(True, alpha=0.4)
    axes[0].set_title("Power dispatch")

    # H2 rate
    axes[1].plot(t, t_out.arH2Dot_total * 1e3, color="forestgreen")
    axes[1].set_ylabel("H₂ rate [mg/s]")
    axes[1].grid(True, alpha=0.4)
    axes[1].set_title("Instantaneous H₂ production rate")

    # Bank temperature
    axes[2].plot(t, t_out.arT_stack, color="darkorange")
    axes[2].set_ylabel("Bank temp [°C]")
    axes[2].grid(True, alpha=0.4)
    axes[2].set_title("Mean bank temperature")

    # Units on
    axes[3].plot(t, t_out.arTotalElectroOn, color="mediumpurple")
    axes[3].set_ylabel("Units on")
    axes[3].set_xlabel("Time [s]")
    axes[3].set_ylim(-0.1, el.iNumUnits + 0.5)
    axes[3].grid(True, alpha=0.4)
    axes[3].set_title("Active electrolyser units")

    plt.tight_layout()
    _maybe_save(fig, save_path)
    return fig, t_out


# ---------------------------------------------------------------------------
# 5.  Thermal banks detail (per bank temperature over one hour)
# ---------------------------------------------------------------------------

def plot_bank_temperatures(
    sim,
    hour: int = 0,
    title: Optional[str] = None,
    save_path: Optional[Union[str, Path]] = None,
):
    """Plot per-bank temperature traces for a single hour.

    Parameters
    ----------
    sim:
        An :class:`R2H2` instance.
    hour:
        Hour index (0-based, default: 0).
    title:
        Axis title override.
    save_path:
        If provided, the figure is saved to this path.

    Returns
    -------
    (fig, t_out) : tuple
    """
    plt = _plt()

    from r2h2.r2h2 import runElectroStackStep1, bank_thermal_from_kind

    sim2 = copy.deepcopy(sim)
    sim2.setUpElectro1()

    el      = sim2.electrolyserunit
    n_banks = el.iN_banks * el.iNumElectro
    th_tmpl = bank_thermal_from_kind(sim2.kind, el, insulated=sim2.insulated)
    th_banks = [copy.deepcopy(th_tmpl) for _ in range(n_banks)]

    P_hour = sim2.windinputs.arPowerInput[:, hour]

    _, t_out, _, _ = runElectroStackStep1(
        sim2.electrocellpem,
        th_banks,
        sim2.battery,
        P_hour,
        sim2.electrolyserunits,
        sim2.windinputs.arTime,
        sim2.simulation,
        hour,
        None,
    )

    t = sim2.windinputs.arTime

    fig, ax = plt.subplots(figsize=(12, 4))
    for b in range(n_banks):
        ax.plot(t, t_out.arT_banks[b, :], label=f"Bank {b + 1}", linewidth=1.5)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Temperature [°C]")
    ax.set_title(title or f"Bank temperatures – hour {hour}")
    ax.legend()
    ax.grid(True, alpha=0.4)
    plt.tight_layout()
    _maybe_save(fig, save_path)
    return fig, t_out


# ---------------------------------------------------------------------------
# 6.  Multi-year summary (one point per year)
# ---------------------------------------------------------------------------

def plot_multi_year_summary(
    out: dict,
    title: Optional[str] = None,
    save_path: Optional[Union[str, Path]] = None,
):
    """Three-panel multi-year summary (only meaningful when ``iNumYears > 1``).

    Panels
    ------
    1. Total H₂ produced per year [kg·s]
    2. Final battery RCD per year
    3. Mean degradation per unit at end of each year [V]

    Parameters
    ----------
    out:
        Return value of :py:meth:`R2H2.run`.
    title:
        Figure suptitle override.
    save_path:
        If provided, the figure is saved to this path.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _plt()

    years = out["YearResults"]
    n_years = len(years)
    x = np.arange(1, n_years + 1)

    total_h2_per_year = np.array([yr["TotalH2"][-1] for yr in years])
    final_rcd         = np.array([yr["Log"]["arRCD"][-1] for yr in years])
    num_units         = years[0]["Log"]["arHourlyDegradation"].shape[0]
    mean_deg_per_year = np.array([
        yr["Log"]["arHourlyDegradation"][:, -1].mean() for yr in years
    ])

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    fig.suptitle(title or "Multi-year simulation summary", fontsize=13)

    axes[0].bar(x, total_h2_per_year / 1e6, color="forestgreen", alpha=0.8)
    axes[0].set_xlabel("Year")
    axes[0].set_ylabel("Total H₂ [kg·s]")
    axes[0].set_title("Annual H₂ production")
    axes[0].grid(True, alpha=0.4, axis="y")
    axes[0].set_xticks(x)

    axes[1].plot(x, final_rcd, marker="o", color="tomato", linewidth=1.5)
    axes[1].set_xlabel("Year")
    axes[1].set_ylabel("RCD")
    axes[1].set_title("Battery RCD (end of year)")
    axes[1].set_ylim(0, 1.05)
    axes[1].grid(True, alpha=0.4)
    axes[1].set_xticks(x)

    axes[2].plot(x, mean_deg_per_year * 1e3, marker="s", color="steelblue", linewidth=1.5)
    axes[2].set_xlabel("Year")
    axes[2].set_ylabel("Mean degradation [mV]")
    axes[2].set_title(f"Mean unit degradation (end of year, {num_units} units)")
    axes[2].grid(True, alpha=0.4)
    axes[2].set_xticks(x)

    plt.tight_layout()
    _maybe_save(fig, save_path)
    return fig


# ---------------------------------------------------------------------------
# 7.  Convenience: produce all standard plots at once
# ---------------------------------------------------------------------------

def plot_all(
    sim,
    out: dict,
    year: int = 0,
    save_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """Generate all standard plots and return them as a dict of Figure objects.

    Plots produced
    --------------
    ``"hourly_overview"``    – :func:`plot_hourly_overview`
    ``"degradation"``        – :func:`plot_degradation`
    ``"battery_fade"``       – :func:`plot_battery_fade`
    ``"second_traces"``      – :func:`plot_second_traces` (hour 0)
    ``"bank_temperatures"``  – :func:`plot_bank_temperatures` (hour 0)
    ``"multi_year_summary"`` – :func:`plot_multi_year_summary` (if > 1 year)

    Parameters
    ----------
    sim:
        An :class:`R2H2` instance.
    out:
        Return value of :py:meth:`R2H2.run`.
    year:
        Year index for hourly/degradation/battery plots (default: 0).
    save_dir:
        Directory in which to save all figures as PNG files.  Created if it
        does not exist.  When ``None`` figures are not saved to disk.

    Returns
    -------
    dict[str, matplotlib.figure.Figure]
        Keys as listed above (``"second_traces"`` key maps to the Figure only,
        not the ``t_out`` tuple).
    """
    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

    def _path(name: str):
        return save_dir / f"{name}.png" if save_dir is not None else None

    figs: dict = {}

    figs["hourly_overview"] = plot_hourly_overview(
        sim, out, year=year, save_path=_path("hourly_overview")
    )
    figs["degradation"] = plot_degradation(
        out, year=year, save_path=_path("degradation")
    )
    figs["battery_fade"] = plot_battery_fade(
        out, year=year, save_path=_path("battery_fade")
    )

    fig_sec, _ = plot_second_traces(sim, hour=0, save_path=_path("second_traces_h0"))
    figs["second_traces"] = fig_sec

    fig_temp, _ = plot_bank_temperatures(sim, hour=0, save_path=_path("bank_temperatures_h0"))
    figs["bank_temperatures"] = fig_temp

    if len(out["YearResults"]) > 1:
        figs["multi_year_summary"] = plot_multi_year_summary(
            out, save_path=_path("multi_year_summary")
        )

    return figs
