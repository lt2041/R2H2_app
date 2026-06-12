# Release Notes — v1.2.12

## Multi-file wind inputs

- Wind inputs linked to a simulation are now ordered by a `sequence` field rather than linked through a simple M2M relation. The new `SimulationWindInput` through-table stores each link's position in the sequence.
- Multiple `WindInput` files can be linked to a single simulation, one per year. The engine concatenates them in sequence order to form the full multi-year wind power array. When multiple files are linked, the `duration_days` override is ignored and the full concatenated length is used.
- Wind inputs can be reordered on the simulation detail page by dragging rows. Changes are persisted immediately via the new `wind-reorder` endpoint.
- Individual wind inputs can be unlinked via a "Not linked" button next to each row. After unlinking, sequence numbers are re-compacted automatically.
- Each wind input entry displays the simulation year it corresponds to. The starting year is derived from `datum_date` and can be edited inline.

## iNumYears removed

- The `iNumYears` field has been removed from the `Simulation` model. The number of simulation years is now always derived automatically from the total length of the concatenated wind data (floor of total hours / 8760, minimum 1). There is no longer a stored or user-settable year count.
- Removed from the simulation detail settings table and all related views.

## Simulation engine — per-year wind slicing

- The engine now slices the concatenated wind array by year offset (`_y_offset = y * hours_per_year`) so each year's loop reads only its own segment of the wind data.
- Per-year output arrays (`arSoc`, `arBatteryRating`, `arSpillPower`, etc.) are sized to `hours_per_year` rather than `num_hours`, keeping each year's HDF5 group compact.
- Progress callback receives `hours_per_year` as the per-year total so the progress bar resets correctly at the start of each year.

## Add and unlink components from simulation detail

- Component groups on the simulation detail page now show an "Add" button that opens a modal listing unlinked instances available to link. Selecting one and confirming POSTs to the existing `link_components` endpoint.
- Each linked component row has a "Not linked" button that POSTs to the new `unlink_component` endpoint, removing the component from the simulation without leaving the page.
- Both actions update the page in-place (no full reload required for the unlink action).

## WindInput start-year editing

- A numeric input above the WindInput list shows the first simulation year. Changing it POSTs to the new `update_first_wind_year` endpoint, which updates `datum_date` on the simulation to match the chosen year (preserving the existing month and day, or defaulting to January 1 if `datum_date` was not set). Valid range: 1900–2300.

## Results page — wind speed from all linked files

- Wind speed data for the results charts is now loaded and concatenated from all linked `WindInput` HDF5 files in sequence order, matching the multi-file engine behaviour. Previously only the first linked file was read.
- `datum_iso` is pinned to 1 January of the datum year so the datetime x-axis always starts at the beginning of the year regardless of the `datum_date` day.

## Results page — consolidated multi-year charts

- Per-year tab panels have been replaced with single continuous charts spanning all simulation years. Each year is rendered as a separate trace (dashed/dotted lines for years 2+) on the same chart.
- The x-axis in hours mode uses a global cumulative hour index across years. In datetime mode all traces share the same time origin derived from `datum_iso`.
- Summary stats aggregate across all years.

## Database migrations

- `0032_simulationwindinput_through` — migrates `wind_inputs` M2M to use `SimulationWindInput` as a through-table; adds `sequence` field; applies `BigAutoField` to all model primary keys.
- `0033_simulationwindinput_year_validators` — adds MinValue/MaxValue validators (1900–2300) to the `year` field on `SimulationWindInput`.
- `0034_alter_simulationwindinput_year` — sets the default year to the current year (2026).
- `0035_alter_simulationwindinput_options_and_more` — changes ordering to `['sequence']`; removes the `year` field from `SimulationWindInput`; updates unique constraint to `(simulation, wind_input)`; renames `datum_date` field placeholder.
- `0036_restore_datum_date` — renames the field back to `datum_date`.
- `0037_remove_inumyears` — removes `iNumYears` from the `Simulation` model.
