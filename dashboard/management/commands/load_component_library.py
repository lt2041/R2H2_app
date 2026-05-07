"""Management command: load_component_library

One-time import utility: reads YAML files from a legacy component_library
directory and upserts matching Django DB records.

This command is only needed when migrating from a YAML-based installation.
All component and simulation parameters are now stored exclusively in the
Django database; YAML files are no longer read at runtime.

Usage
-----
  python manage.py load_component_library
  python manage.py load_component_library --dry-run
  python manage.py load_component_library --library-dir /path/to/dir
"""
from __future__ import annotations

import math
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError

from dashboard.models import (
    Battery,
    ElectroCellPEM,
    ElectrolyserUnit,
    ThermalProperties,
    TimeOutput,
    WindInput,
)

# ── Model registry: YAML filename prefix → Django model ──────────────────────
MODEL_MAP = {
    "Battery":           Battery,
    "ElectroCellPEM":    ElectroCellPEM,
    "ElectrolyserUnit":  ElectrolyserUnit,
    "ThermalProperties": ThermalProperties,
    "TimeOutputs":       TimeOutput,
    "WindInputs":        WindInput,
}

# ── Known field-name remaps: YAML key → model field name ─────────────────────
# Only entries where they differ are listed.
FIELD_REMAP = {
    Battery: {
        "rKt":  "rKt_lc",   # Battery YAML uses rKt; model uses rKt_lc
        "rKT":  "rKT_uc",   # Battery YAML uses rKT; model uses rKT_uc
    },
}

# ── YAML values that should be treated as None in the DB ─────────────────────
_NULL_SENTINELS = {None, "null", "NULL", "Null", "none", "None", "float"}


def _flatten(d: dict, parent_key: str = "") -> dict:
    """Recursively flatten a nested dict into a single-level dict.

    Nested section keys (e.g. ``degradation``, ``operational``) are
    discarded; only the leaf key names are kept, mirroring how
    :class:`r2h2.components.base.ComponentBase` sets attributes.
    """
    items: dict = {}
    for k, v in d.items():
        if isinstance(v, dict):
            items.update(_flatten(v, k))
        else:
            items[k] = v
    return items


def _coerce(value):
    """Convert YAML-parsed values to DB-safe Python types.

    * Null sentinels → None
    * ``inf`` floats are kept as-is (SQLite stores IEEE 754 inf correctly)
    * Everything else passes through.
    """
    if value in _NULL_SENTINELS:
        return None
    return value


def _model_fields(model) -> set[str]:
    """Return the set of concrete field names for a model (excludes id, name)."""
    return {
        f.name
        for f in model._meta.get_fields()
        if hasattr(f, "column")  # concrete DB column
    } - {"id", "name"}


class Command(BaseCommand):
    help = "Upsert Django DB records from YAML files in the component library directory."

    def add_arguments(self, parser):
        parser.add_argument(
            "--library-dir",
            type=str,
            default=None,
            help="Path to component_library directory (defaults to <data_root>/component_library).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Parse and validate YAML files without writing to the DB.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # ── Resolve library directory ─────────────────────────────────────
        if options["library_dir"]:
            lib_dir = Path(options["library_dir"])
        else:
            import r2h2.config as r2h2_cfg
            lib_dir = Path(r2h2_cfg.Paths().data_root) / "component_library"

        if not lib_dir.is_dir():
            raise CommandError(f"Component library directory not found: {lib_dir}")

        yaml_files = sorted(lib_dir.glob("*.yaml"))
        if not yaml_files:
            self.stdout.write(self.style.WARNING(f"No YAML files found in {lib_dir}"))
            return

        self.stdout.write(f"Loading from: {lib_dir}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be written."))

        created_total = updated_total = skipped_total = 0

        for yaml_path in yaml_files:
            stem = yaml_path.stem  # e.g. "Battery-0", "ThermalProperties-0"

            # ── Determine which model this file belongs to ────────────────
            model = None
            prefix = None
            for key, mdl in MODEL_MAP.items():
                if stem.startswith(key):
                    model = mdl
                    prefix = key
                    break

            if model is None:
                self.stdout.write(
                    self.style.WARNING(f"  {yaml_path.name}: no matching model — skipping")
                )
                skipped_total += 1
                continue

            # ── Parse YAML ────────────────────────────────────────────────
            try:
                raw = yaml.safe_load(yaml_path.read_text())
            except yaml.YAMLError as exc:
                self.stdout.write(
                    self.style.ERROR(f"  {yaml_path.name}: YAML parse error — {exc}")
                )
                skipped_total += 1
                continue

            if not isinstance(raw, dict):
                self.stdout.write(
                    self.style.WARNING(f"  {yaml_path.name}: unexpected YAML structure — skipping")
                )
                skipped_total += 1
                continue

            flat = _flatten(raw)

            # ── Apply field-name remaps ────────────────────────────────────
            remap = FIELD_REMAP.get(model, {})
            remapped: dict = {}
            for k, v in flat.items():
                remapped[remap.get(k, k)] = _coerce(v)

            # ── Filter to fields that exist on the model ───────────────────
            valid_fields = _model_fields(model)
            kwargs = {k: v for k, v in remapped.items() if k in valid_fields}

            unknown = set(remapped) - valid_fields - {"id", "name"}
            if unknown:
                self.stdout.write(
                    self.style.WARNING(
                        f"  {yaml_path.name}: ignoring unknown fields: {sorted(unknown)}"
                    )
                )

            if not kwargs:
                self.stdout.write(
                    self.style.WARNING(f"  {yaml_path.name}: no mappable fields — skipping")
                )
                skipped_total += 1
                continue

            # ── Upsert by name (stem of filename used as record name) ──────
            record_name = stem  # e.g. "Battery-0"

            if dry_run:
                action = "CREATE/UPDATE"
                self.stdout.write(
                    f"  {yaml_path.name} → {model.__name__}(name='{record_name}') "
                    f"[{len(kwargs)} fields]  [{action}]"
                )
                continue

            obj, created = model.objects.update_or_create(
                name=record_name,
                defaults=kwargs,
            )

            action = "created" if created else "updated"
            style_fn = self.style.SUCCESS if created else self.style.HTTP_INFO
            self.stdout.write(
                style_fn(
                    f"  {yaml_path.name} → {model.__name__}(id={obj.pk}, name='{record_name}') "
                    f"[{len(kwargs)} fields]  [{action}]"
                )
            )
            if created:
                created_total += 1
            else:
                updated_total += 1

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDone. created={created_total}  updated={updated_total}  skipped={skipped_total}"
                )
            )
