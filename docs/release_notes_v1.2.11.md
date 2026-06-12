# Release Notes — v1.2.11

## Battery replacement logic

- Battery replacement is now triggered when the rated energy capacity falls below a configurable threshold fraction of the initial capacity, replacing the previous logic which triggered on an SoC out-of-bounds condition.
- New field `rReplacementThreshold` (default 0.7) controls the threshold. A value of 0.7 means the battery is replaced when its rated capacity drops below 70% of its original value.
- `rReplacementThreshold` is exposed in the Battery edit modal under the General group.

## Spill power recorded

- `arSpillPower` is now computed each hour as the difference between the demanded battery power and the effective (capacity-limited) power, and logged to the HDF5 output file per year.
- The results page summary shows total spill energy (kWh) aggregated across all years.

## H2 production units corrected

- The `TotalH2` array stored in the HDF5 output and used throughout the application represents cumulative hydrogen production in **grams**, not g/s·s. Labels, axis titles, and documentation have been updated accordingly (plots now show t H2 on the y-axis instead of kg·s).
- Matplotlib and Plotly plot helpers (`_plots_mpl.py`, `_plots_plotly.py`) updated to label the y-axis "t H2".
- Developer documentation (`dev_notes_simulation_engine.md`) and demo script (`tests/r2h2_demo.py`) updated with correct units.

## Delete simulation

- A "Delete Model" button is available on the simulation detail page.
- Clicking it shows a confirmation dialog, then POSTs to a new `delete_simulation` endpoint.
- Deletion is blocked if any run for that simulation is currently pending or running; an error message is shown in that case.
- On success the user is redirected to the simulations list.

## TimeOutput removed as a user-selectable component

- `TimeOutput` is no longer shown as a linkable component when creating or editing a simulation. It is an internal engine output container and does not need to be managed by users.
- Removed from the create/update simulation M2M maps, the simulations list view, and all related templates.

## Simulation detail — hidden settings panel

- Simulation-level settings that are not in the primary settings table (e.g. `rTotalTime`, `rTransientSteps`, `bSingleTurb`, `arLateralDistances`) now appear in a collapsible "Other fields" sub-panel below the main settings table, matching the component badge pattern introduced in v1.2.10.

## Results page — summary stats updated

- The per-year summary stat row now shows: total H2 produced, battery rated capacity at end of year (kWh), total spill energy (kWh), and battery replacement count.
- Replaced the earlier "mean end-of-simulation efficiency" and "end-of-simulation rated capacity %" stats with the above.

## Help page

- Added a "Controller causality" tip: custom controllers must only use input data up to and including the current time step index and must not read future samples.

## README

- Added Ubuntu prerequisite install instructions for `git` and `pip` for systems that do not have them pre-installed.

## Django settings

- `DEFAULT_AUTO_FIELD` set to `django.db.models.BigAutoField` in `r2h2_ui/settings.py`.

## Database migrations

- `0030_alter_battery_rbatteryrating_and_more` — updates help text for `rBatteryRating`, `rControlTargetSoC`, and `rInitialBatteryRating`.
- `0031_add_battery_replacement_threshold` — adds `rReplacementThreshold` field to the Battery model.
