# Release Notes — v1.2.9

## Battery model improvements

- Renamed battery degradation fields for clarity:
  - `rKT_uc` → `KTemp` (temperature degradation factor)
  - `rKt_lc` → `fKt` (elapsed-time degradation factor)
- Added `help_text` descriptions to all Battery fields.
- Reorganised Battery field layout into logical sections: General, Degradation, SEI Film.
- Added `editable_groups` metadata to Battery, ElectroCellPEM, ElectrolyserUnit, and ThermalProperties models, defining which fields appear in which edit-modal section.

## Component browse UI

- Edit modals for components with `editable_groups` now display fields in labelled sections (e.g. General, Degradation, SEI Film) rather than a flat list.
- The main component table now shows grouped parameter badges (field name + value) instead of raw column values for grouped models.
- Table header background colour updated.
- Number inputs in edit modals now use formatted display values (thousand-comma separators for normal-range numbers; scientific notation for very small or very large values).
- Comma characters are stripped when parsing float and integer field values on save, so formatted inputs are accepted correctly.
- Added `zip` and `fmt_float` template filters to `browse_extras.py`.
- Edit modal title now uses the model's `verbose_name` rather than the URL table name.

## Help page

- Added GitHub repository link to the About table.

## README

- Rewrote README to be concise: covers pipx install, developer editable install, first-launch workflow, and key notes. Removed outdated Anaconda/PyCharm-specific sections.

## Database migrations

- `0026_rename_rkt_uc_battery_ktemp` — renames `rKT_uc` to `KTemp`.
- `0027_rename_rkt_lc_battery_fkt` — renames `rKt_lc` to `fKt`; updates help text for all Battery fields; sets `AutoField` primary keys on all models.
- `0028_alter_battery_fkt` — updates `fKt` help text and default.
