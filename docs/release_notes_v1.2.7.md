# Release Notes — v1.2.7

## Component defaults — YAML dependency removed

- Component classes (`Battery`, `ElectroCellPEM`, `ElectrolyserUnit`, `ThermalProperties`, `TimeOutputs`, `WindInputs`) now define their own default parameter values as plain Python attributes in `__init__`, replacing the previous YAML file lookups.
- `ComponentBase` no longer imports `yaml` or reads any YAML files. The `config_path` constructor parameter and all YAML helper methods (`_load_defaults`, `_get_all_fields`, `_merge_configs`) have been removed.
- `ComponentBase.__init__` now accepts only `orm_object`; subclass defaults are set first, then the ORM values are applied on top if an instance is provided.
- `R2H2.update_component` docstring updated to reflect the removal of the `.yaml`/`.yml` extension-stripping fallback.

## HDF5 dependency

- `h5py >= 3.11.0` added as a package dependency in `pyproject.toml` for HDF5 wind-data I/O.

## In-app update UI (initial implementation)

- A "Check for updates" button is available on the Help page.
- Clicking it POSTs to a new `git_pull` endpoint (`/help/git-pull/`) which runs `git pull` in the project root and returns stdout/stderr as JSON.
- The result is shown in a modal: if changes were pulled the modal includes a restart note with the command to rerun.

## HDF5 output download

- Run output download links now use a dedicated view (`download_run_output`) instead of a raw media URL.
- The view serves the file with `Content-Type: application/x-hdf5` and `Content-Disposition: attachment`, preventing browsers (e.g. Safari) from appending a spurious `.html` suffix.
- New URL: `simulations/<sim_id>/run/<run_id>/download/`.

## Help page

- Removed the "Component Library YAML import" tip card (no longer applicable after the YAML removal).
