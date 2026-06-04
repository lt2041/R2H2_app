#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
r2h2._plots_plotly
==================
Plotly backend for r2h2 standard results plots.

Do not import this module directly — use :mod:`r2h2.plots` instead.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Optional, Union

import numpy as np


# ---------------------------------------------------------------------------
# Lazy plotly import
# ---------------------------------------------------------------------------

def _go():
    try:
        import plotly.graph_objects as go
        return go
    except ImportError as exc:
        raise ImportError(
            "plotly is required for interactive plotting.  "
            "Install it with:  pip install plotly"
        ) from exc


def _make_subplots(*args, **kwargs):
    try:
        from plotly.subplots import make_subplots
        return make_subplots(*args, **kwargs)
    except ImportError as exc:
        raise ImportError(
            "plotly is required.  Install it with:  pip install plotly"
        ) from exc


# ---------------------------------------------------------------------------
# Colour palette (mirrors matplotlib colours used in the mpl backend)
# ---------------------------------------------------------------------------

_C = {
    "blue":   "#4682B4",   # steelblue
    "green":  "#228B22",   # forestgreen
    "orange": "#FF8C00",   # darkorange
    "purple": "#9370DB",   # mediumpurple
    "red":    "#FF6347",   # tomato
    "gray":   "#808080",
}

_LAYOUT = dict(
    template="plotly_white",
    font=dict(size=12),
    margin=dict(l=60, r=30, t=60, b=50),
)


# ---------------------------------------------------------------------------
# Save helper
# ---------------------------------------------------------------------------

def _maybe_save(fig, save_path: Optional[Union[str, Path]]) -> None:
    if save_path is None:
        return
    save_path = Path(save_path)
    suffix = save_path.suffix.lower()
    if suffix == ".html":
        fig.write_html(str(save_path))
    elif suffix in (".png", ".jpg", ".jpeg", ".svg", ".pdf"):
        try:
            fig.write_image(str(save_path))
        except Exception as exc:
            raise RuntimeError(
                f"Could not write image to {save_path}.  "
                "Static image export requires kaleido:  pip install kaleido"
            ) from exc
    else:
        # default: HTML
        fig.write_html(str(save_path))


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
    go = _go()

    log      = out["YearResults"][year]["Log"]
    total_h2 = out["YearResults"][year]["TotalH2"]
    num_hours = len(log["arSoc"])
    hours     = np.arange(num_hours)
    num_units = sim.electrolyserunit.iNumUnits
    P_wind_avg = sim.windinputs.arPowerInput.mean(axis=0)[:num_hours]

    fig = _make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        subplot_titles=[
            "Available wind power",
            "Cumulative hydrogen production",
            "Battery state of charge",
            f"Electrolyser utilisation (max {num_units} units)",
        ],
        vertical_spacing=0.07,
    )

    fig.add_trace(go.Scatter(
        x=hours, y=P_wind_avg / 1e6,
        mode="lines", name="Wind power",
        line=dict(color=_C["blue"], width=2),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=hours, y=total_h2 / 1e6,
        mode="lines", name="Cumulative H₂",
        line=dict(color=_C["green"], width=2),
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=hours, y=log["arSoc"] * 100,
        mode="lines", name="Battery SoC",
        line=dict(color=_C["orange"], width=2),
        ), row=3, col=1)
    # SoC reference line
    fig.add_hline(y=50, line=dict(color=_C["gray"], dash="dash", width=1),
                  annotation_text="SoC ref 50 %", annotation_position="top right",
                  row=3, col=1)

    fig.add_trace(go.Bar(
        x=hours, y=log["arElecOnAv"] / num_units * 100,
        name="Units on %",
        marker_color=_C["purple"], opacity=0.8,
    ), row=4, col=1)

    fig.update_yaxes(title_text="Wind power [MW]",   row=1, col=1)
    fig.update_yaxes(title_text="Cumulative H₂ [t]", row=2, col=1)
    fig.update_yaxes(title_text="Battery SoC [%]", range=[0, 100], row=3, col=1)
    fig.update_yaxes(title_text="Units on [%]",    range=[0, 105], row=4, col=1)
    fig.update_xaxes(title_text="Hour", row=4, col=1)

    fig.update_layout(
        title_text=title or f"R2H2 Simulation – hourly overview (year {year + 1})",
        height=900, showlegend=False,
        **_LAYOUT,
    )

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
    go = _go()

    log = out["YearResults"][year]["Log"]
    deg = log["arHourlyDegradation"]
    hours = np.arange(deg.shape[1])

    fig = go.Figure()
    for i in range(deg.shape[0]):
        fig.add_trace(go.Scatter(
            x=hours, y=deg[i, :],
            mode="lines", name=f"Unit {i + 1}",
            line=dict(width=2),
        ))

    fig.update_layout(
        title_text=title or "Electrolyser unit degradation (summed, per unit)",
        xaxis_title="Hour",
        yaxis_title="Cumulative degradation [V]",
        height=350,
        **_LAYOUT,
    )

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
    go = _go()

    log   = out["YearResults"][year]["Log"]
    hours = np.arange(len(log["arSoc"]))

    rcd_min = max(0.0, float(np.min(log["arRCD"])) - 0.01)
    rcd_max = min(1.0, float(np.max(log["arRCD"])) + 0.01)

    fig = _make_subplots(
        rows=1, cols=2,
        subplot_titles=["Battery capacity (GJ)", "Remaining capacity fraction"],
        horizontal_spacing=0.12,
    )

    fig.add_trace(go.Scatter(
        x=hours, y=log["arBatteryRating"] / 1e9,
        mode="lines", name="Rating",
        line=dict(color=_C["orange"], width=2),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=hours, y=log["arRCD"],
        mode="lines", name="RCD",
        line=dict(color=_C["red"], width=2),
    ), row=1, col=2)

    fig.update_xaxes(title_text="Hour", row=1, col=1)
    fig.update_xaxes(title_text="Hour", row=1, col=2)
    fig.update_yaxes(title_text="Battery rating [GJ]", row=1, col=1)
    fig.update_yaxes(title_text="RCD (remaining capacity)",
                     range=[rcd_min, rcd_max], row=1, col=2)

    fig.update_layout(
        title_text=title or "Battery degradation",
        height=400, showlegend=False,
        **_LAYOUT,
    )

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
    go = _go()

    from r2h2.r2h2 import runElectroStackStep1, bank_thermal_from_kind

    sim2 = copy.deepcopy(sim)
    sim2.setUpElectro1()

    el      = sim2.electrolyserunit
    n_banks = el.iN_banks * el.iNumElectro
    th_tmpl = bank_thermal_from_kind(sim2.kind, el, insulated=sim2.insulated)
    th_banks = [copy.deepcopy(th_tmpl) for _ in range(n_banks)]
    P_hour = sim2.windinputs.arPowerInput[:, hour]

    units, t_out, _, _ = runElectroStackStep1(
        sim2.electrocellpem, th_banks, sim2.battery, P_hour,
        sim2.electrolyserunits, sim2.windinputs.arTime,
        sim2.simulation, hour, None,
    )

    t = sim2.windinputs.arTime

    fig = _make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        subplot_titles=[
            "Power dispatch",
            "Instantaneous H₂ production rate",
            "Mean bank temperature",
            "Active electrolyser units",
        ],
        vertical_spacing=0.07,
    )

    fig.add_trace(go.Scatter(
        x=t, y=t_out.arAvailablePower / 1e6,
        mode="lines", name="Available",
        line=dict(color=_C["blue"], width=2),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=t, y=t_out.arP_el_total / 1e6,
        mode="lines", name="Electrolyser demand",
        line=dict(color=_C["red"], width=2),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=t, y=t_out.arH2Dot_total * 1e3,
        mode="lines", name="H₂ rate",
        line=dict(color=_C["green"], width=2), showlegend=False,
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=t, y=t_out.arT_stack,
        mode="lines", name="Bank temp",
        line=dict(color=_C["orange"], width=2), showlegend=False,
    ), row=3, col=1)

    fig.add_trace(go.Scatter(
        x=t, y=t_out.arTotalElectroOn,
        mode="lines", name="Units on",
        line=dict(color=_C["purple"], width=2), showlegend=False,
    ), row=4, col=1)

    fig.update_yaxes(title_text="Power [MW]",      row=1, col=1)
    fig.update_yaxes(title_text="H₂ rate [mg/s]",  row=2, col=1)
    fig.update_yaxes(title_text="Bank temp [°C]",  row=3, col=1)
    fig.update_yaxes(title_text="Units on",
                     range=[-0.1, el.iNumUnits + 0.5], row=4, col=1)
    fig.update_xaxes(title_text="Time [s]", row=4, col=1)

    fig.update_layout(
        title_text=title or f"Per-second traces – hour {hour}",
        height=900, legend=dict(x=0.75, y=0.99),
        **_LAYOUT,
    )

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
    go = _go()

    from r2h2.r2h2 import runElectroStackStep1, bank_thermal_from_kind

    sim2 = copy.deepcopy(sim)
    sim2.setUpElectro1()

    el      = sim2.electrolyserunit
    n_banks = el.iN_banks * el.iNumElectro
    th_tmpl = bank_thermal_from_kind(sim2.kind, el, insulated=sim2.insulated)
    th_banks = [copy.deepcopy(th_tmpl) for _ in range(n_banks)]
    P_hour = sim2.windinputs.arPowerInput[:, hour]

    _, t_out, _, _ = runElectroStackStep1(
        sim2.electrocellpem, th_banks, sim2.battery, P_hour,
        sim2.electrolyserunits, sim2.windinputs.arTime,
        sim2.simulation, hour, None,
    )

    t = sim2.windinputs.arTime

    fig = go.Figure()
    for b in range(n_banks):
        fig.add_trace(go.Scatter(
            x=t, y=t_out.arT_banks[b, :],
            mode="lines", name=f"Bank {b + 1}",
            line=dict(width=2),
        ))

    fig.update_layout(
        title_text=title or f"Bank temperatures – hour {hour}",
        xaxis_title="Time [s]",
        yaxis_title="Temperature [°C]",
        height=350,
        **_LAYOUT,
    )

    _maybe_save(fig, save_path)
    return fig, t_out


# ---------------------------------------------------------------------------
# 6.  Multi-year summary
# ---------------------------------------------------------------------------

def plot_multi_year_summary(
    out: dict,
    title: Optional[str] = None,
    save_path: Optional[Union[str, Path]] = None,
):
    go = _go()

    years = out["YearResults"]
    n_years = len(years)
    x = list(range(1, n_years + 1))

    total_h2_per_year = np.array([yr["TotalH2"][-1] for yr in years])
    final_rcd         = np.array([yr["Log"]["arRCD"][-1] for yr in years])
    num_units         = years[0]["Log"]["arHourlyDegradation"].shape[0]
    mean_deg_per_year = np.array([
        yr["Log"]["arHourlyDegradation"][:, -1].mean() for yr in years
    ])

    fig = _make_subplots(
        rows=1, cols=3,
        subplot_titles=[
            "Annual H₂ production",
            "Battery RCD (end of year)",
            f"Mean unit degradation (end of year, {num_units} units)",
        ],
        horizontal_spacing=0.1,
    )

    fig.add_trace(go.Bar(
        x=x, y=total_h2_per_year / 1e6,
        name="H₂", marker_color=_C["green"], opacity=0.8,
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=x, y=final_rcd,
        mode="lines+markers", name="RCD",
        line=dict(color=_C["red"], width=2), marker=dict(size=8),
    ), row=1, col=2)

    fig.add_trace(go.Scatter(
        x=x, y=mean_deg_per_year * 1e3,
        mode="lines+markers", name="Degradation",
        line=dict(color=_C["blue"], width=2), marker=dict(symbol="square", size=8),
    ), row=1, col=3)

    fig.update_xaxes(title_text="Year", tickvals=x, row=1, col=1)
    fig.update_xaxes(title_text="Year", tickvals=x, row=1, col=2)
    fig.update_xaxes(title_text="Year", tickvals=x, row=1, col=3)
    fig.update_yaxes(title_text="Total H₂ [t]",       row=1, col=1)
    fig.update_yaxes(title_text="RCD", range=[0, 1.05],   row=1, col=2)
    fig.update_yaxes(title_text="Mean degradation [mV]",  row=1, col=3)

    fig.update_layout(
        title_text=title or "Multi-year simulation summary",
        height=400, showlegend=False,
        **_LAYOUT,
    )

    _maybe_save(fig, save_path)
    return fig


# ---------------------------------------------------------------------------
# 7.  plot_all
# ---------------------------------------------------------------------------

def plot_all(
    sim,
    out: dict,
    year: int = 0,
    save_dir: Optional[Union[str, Path]] = None,
) -> dict:
    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

    def _path(name: str):
        return save_dir / f"{name}.html" if save_dir is not None else None

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
