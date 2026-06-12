# Release Notes — v1.2.10

## Simulation results — power traces added

- Wind power, available power, and electrolyser demand are now recorded to the HDF5 output file for every simulation hour (in a `power` sub-group per year).
- The hourly values are averaged over the intra-hour timesteps, skipping the transient warm-up period (`rTransientSteps`), giving cleaner hourly means.
- The results page plots Wind, Electrolyser, and Battery (Wind minus Electrolyser) power on a dedicated chart.

## Simulation results — per-unit electrolyser degradation

- Hourly degradation is now stored as a 2-D array `[n_units, n_hours]` per year group, preserving per-unit traces.
- The results page plots one efficiency trace per electrolyser unit (% of original efficiency).
- The number of units (`iNumUnits`) is written as an attribute on the `electrolyser` group and read back when rendering the "electrolysers switched on %" chart, so the percentage is correctly normalised.

## Simulation results — battery SoC rescaled to fraction of original capacity

- The SoC chart now shows SoC as a fraction of the original (day-zero) battery rated capacity, rather than a fraction of the current (degraded) capacity. This makes long-run capacity fade visible on the same axis as SoC.

## Battery model — `rControlMinSoC` renamed to `rControlTargetSoC`

- The battery field previously named `rControlMinSoC` is renamed to `rControlTargetSoC` to reflect its actual role: it is the target SoC that the proportional controller drives toward, not a minimum bound.
- Updated in: `dashboard/models.py`, `r2h2/components/Battery.py`, `r2h2/defaults/battery.yaml`, `r2h2/r2h2.py` (`dynamicControl`), the controller template, and all related UI labels.
- The built-in controller template (`controller_template.py`) is updated to use `battery.rControlTargetSoC` and includes a clarifying comment distinguishing it from `rSoCRef` (which is used by the degradation model, not for control).

## Simulation detail — component badge groups

- Component settings panels in the simulation detail view now display parameters as grouped badge widgets (matching the browse page style) for models that define `editable_groups`.
- Fields in `ui_display_fields` that are not in any `editable_groups` group appear in a collapsible "Other fields" sub-panel.
- Numeric values in the simulation detail settings table are formatted with `fmt_float` (thousand commas / scientific notation as appropriate).

## Database migrations

- `0029_rename_rcontrolminsoc_battery_rcontroltargetsoc` — renames `rControlMinSoC` to `rControlTargetSoC`.
