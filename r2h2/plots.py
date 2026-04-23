#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
r2h2.plots
==========
Standard results plots for an R2H2 simulation run.

Two rendering backends are supported:

* ``"plotly"``     – interactive HTML figures (default).
* ``"matplotlib"`` – static PNG-quality figures.

Usage
-----
    from r2h2.plots import plot_all, plot_hourly_overview

    out = sim.run()

    # Interactive (plotly, default)
    figs = plot_all(sim, out)

    # Static matplotlib
    figs = plot_all(sim, out, backend="matplotlib")

    # Individual plot, explicit backend
    fig = plot_hourly_overview(sim, out, backend="plotly")
    fig = plot_hourly_overview(sim, out, backend="matplotlib")

All functions accept ``save_path`` (single plot) or ``save_dir`` (plot_all).
For the plotly backend, ``save_path`` should end in ``.html`` (default) or
``.png``/``.svg``/``.pdf`` (requires ``pip install kaleido``).
For the matplotlib backend, any image extension accepted by ``savefig`` works.

The default backend can be changed globally::

    import r2h2.plots as plots
    plots.DEFAULT_BACKEND = "matplotlib"
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional, Union

import numpy as np

# ---------------------------------------------------------------------------
# Global default
# ---------------------------------------------------------------------------

DEFAULT_BACKEND: Literal["plotly", "matplotlib"] = "plotly"


# ---------------------------------------------------------------------------
# Backend dispatch
# ---------------------------------------------------------------------------

def _backend(name: Optional[str]):
    b = (name or DEFAULT_BACKEND).lower()
    if b in ("plotly", "ply"):
        from r2h2 import _plots_plotly as _ply
        return _ply
    if b in ("matplotlib", "mpl"):
        from r2h2 import _plots_mpl as _mpl
        return _mpl
    raise ValueError(
        f"Unknown plotting backend {name!r}.  "
        "Choose 'plotly' (default) or 'matplotlib'."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def plot_hourly_overview(sim, out, year=0, title=None, save_path=None, backend=None):
    """Four-panel hourly overview: wind power, H2, SoC, utilisation."""
    return _backend(backend).plot_hourly_overview(sim, out, year=year, title=title, save_path=save_path)


def plot_degradation(out, year=0, title=None, save_path=None, backend=None):
    """Cumulative per-unit electrolyser degradation vs hour."""
    return _backend(backend).plot_degradation(out, year=year, title=title, save_path=save_path)


def plot_battery_fade(out, year=0, title=None, save_path=None, backend=None):
    """Two-panel battery capacity fade: rating [GJ] and RCD fraction."""
    return _backend(backend).plot_battery_fade(out, year=year, title=title, save_path=save_path)


def plot_second_traces(sim, hour=0, title=None, save_path=None, backend=None):
    """Four-panel per-second traces for one hour. Returns (fig, t_out)."""
    return _backend(backend).plot_second_traces(sim, hour=hour, title=title, save_path=save_path)


def plot_bank_temperatures(sim, hour=0, title=None, save_path=None, backend=None):
    """Per-bank temperature traces for one hour. Returns (fig, t_out)."""
    return _backend(backend).plot_bank_temperatures(sim, hour=hour, title=title, save_path=save_path)


def plot_multi_year_summary(out, title=None, save_path=None, backend=None):
    """Three-panel multi-year summary: H2, RCD, degradation."""
    return _backend(backend).plot_multi_year_summary(out, title=title, save_path=save_path)


def plot_all(sim, out, year=0, save_dir=None, backend=None) -> dict:
    """Generate all standard plots. Returns dict[str, Figure].

    Keys: 'hourly_overview', 'degradation', 'battery_fade',
          'second_traces', 'bank_temperatures', 'multi_year_summary' (if >1 year).

    Parameters
    ----------
    backend : str, optional
        ``'plotly'`` (default, interactive) or ``'matplotlib'`` (static).
        Override globally with ``r2h2.plots.DEFAULT_BACKEND = 'matplotlib'``.
    save_dir : path, optional
        Directory to save figures. Plotly saves .html; matplotlib saves .png.
    """
    return _backend(backend).plot_all(sim, out, year=year, save_dir=save_dir)
