# Release Notes — v1.2.6

**Released:** 12 May 2026

---

## Summary

v1.2.6 delivers a complete engineering-controller workflow (create, edit, rename, run), a first-class `Controller` database model, automatic seeding of a pre-configured "Main Model" simulation on first run, removal of the legacy `Simulation.yaml` component-list dependency, and a new in-app Help page.

---

## What's new

### Pluggable engineering controllers

Users can now supply a custom Python controller file that replaces the built-in `dynamicControl` dispatch logic for a given simulation.

- New `Simulation.controller_file` field (migration `0022`) records the selected controller filename.
- A CodeMirror browser editor is embedded in the simulation detail page, with syntax highlighting, save/load actions, and a warnings panel for dangerous patterns or syntax errors.
- Server-side endpoints: list, get, save, and assign controller files, with filename validation and path-traversal protection.
- A built-in controller template (`r2h2/defaults/controller_template.py`) is seeded automatically into `<data_root>/controllers/` via `get_controllers_dir()`.
- At runtime, the selected controller module is loaded dynamically and invoked through a safety wrapper that enforces a 30-second per-call timeout, validates the return values, and falls back to `dynamicControl` on any error.

### Controller model and full CRUD UI

A dedicated `Controller` database model now backs every controller file.

- `Controller` has fields: `file` (FileField, unique, stored in `<data_root>/controllers/`), `name`, `description`, `author`, `date_created`, `verified`, and `edit_history` (JSON list of timestamped edits).
- Migrations `0023`–`0025` create the model, add the `edit_history` field, and convert the legacy `filename` CharField to a FileField in a state-only migration (no database change).
- Django admin integration with search, list display, filters, and an edit-count computed column.
- `AppConfig.post_migrate` seeds the built-in `default_controller.py` record automatically.
- Management command `ensure_default_controller` provides a manual seed path.
- Simulation model gains a `controller` ForeignKey to `Controller` (alongside the legacy `controller_file` CharField for backwards compatibility).
- Simulation detail UI: controller selector (browser-default styling to bypass Materialize), inline rename row, and a light-themed "New Controller" modal with a "Duplicate from" dropdown populated from the existing file list via JavaScript. Client-side validation enforces lowercase-and-underscore names and blocks duplicates or renaming the built-in template.
- Save flow appends an `edit_history` entry on every save; rename flow moves the disk file, updates the `Controller.file` field, and cascades the legacy `Simulation.controller_file` references.

### Main Model auto-seed

A "Main Model" simulation and its associated components are now created automatically on first run.

- Management command `create_main_model` bootstraps a `Simulation` named "Main Model" with linked `Battery`, `ElectroCellPEM`, `ElectrolyserUnit`, and `ThermalProperties` records, all named with a "Main " prefix and populated from the reference-data PEM defaults. Supports `--kind PEM|ALK` and `--overwrite`.
- A `post_migrate` signal handler in `AppConfig.ready()` calls `_seed_main_model()` silently after every migration, creating the Main Model objects if they do not exist. Exceptions are swallowed to avoid failures during the initial migrate when tables may not yet exist.

### Simulation component defaults — YAML dependency removed

Component classes no longer read YAML files at runtime.

- `r2h2/components/base.py`: `ComponentBase` no longer imports `yaml` or reads any YAML files. The `config_path` parameter and all YAML helper methods (`_load_defaults`, `_get_all_fields`, `_merge_configs`) have been removed. The base class now only handles ORM-instance loading and `from_django`.
- Each component class (`Battery`, `ElectroCellPEM`, `ElectrolyserUnit`, `ThermalProperties`, `TimeOutputs`, `WindInputs`) now defines its own defaults as plain Python attributes in `__init__`, replacing the YAML files in `r2h2/defaults/`.
- `r2h2/components/Simulation.py` is a plain Python settings container (no `ComponentBase` inheritance).
- `R2H2.__init__` instantiates components from a hardcoded `_COMPONENT_CLASSES` list.
- `R2H2.update_component` docstring and body updated — legacy `.yaml`/`.yml` extension stripping removed.
- Controller lookup in `R2H2.run()` reads `simulation.controller.filename` via the FK rather than the legacy `controller_file` CharField.

### Help page

A new Help & Guide page is available from the sidebar.

- Displays the installed package version, Django version, and Python version.
- Includes a numbered Getting Started workflow, a Custom Controllers section (what they are, how to create one, timeout behaviour), Quick Tips (duplicate simulation, datum date, duration limit, YAML import, re-seed Main Model, cancel a run), and an About table.
- Wired into the base template sidebar and the URL configuration.

---

## Migrations

| Migration | Description |
|---|---|
| `0022_simulation_controller_file` | Adds `Simulation.controller_file` CharField |
| `0023_controller_model_and_fk` | Creates `Controller` model and `Simulation.controller` FK |
| `0024_controller_edit_history` | Adds `Controller.edit_history` JSONField |
| `0025_controller_filename_to_filefield` | Converts `Controller.filename` CharField to FileField (state-only, no DB change) |

---

## Bug fixes and minor changes

- README updated with revised installation instructions, `pipx` recommendation, Anaconda/conda walkthrough, and a "Check your installation" section.
- `.gitignore` updated to exclude `reference_data` directories and fix `.ipynb` entry formatting.

---

## Upgrade notes

Run migrations after upgrading:

```
python manage.py migrate
```

The Main Model simulation and its components will be seeded automatically during the migration step. To force a reset of the Main Model:

```
python manage.py create_main_model --overwrite
```
