import yaml
from pathlib import Path
from typing import Optional, Any

class ComponentBase:
    """
    Base class for all components in R2H2. Handles loading parameters from
    YAML files, default dicts, or Django ORM model instances.
    """

    def __init__(self, config_path: Optional[str] = None, orm_object: Any = None):
        """
        Initialise component parameters.

        Priority order:
          1. ``orm_object``  – a Django model instance; field values are read
                               directly from its attributes (no YAML involved).
          2. ``config_path`` – path to a YAML file merged on top of defaults.
          3. neither          – defaults only.

        Args:
            config_path: Path to a YAML configuration file.
            orm_object:  A Django model instance whose attribute names match
                         the component's parameter names.
        """
        if orm_object is not None:
            self._load_from_orm(orm_object)
            return

        # Convert config_path to Path object if provided
        if config_path is not None:
            config_path = Path(config_path)

        # Load defaults
        defaults = self._load_defaults(None)

        # If custom config provided, validate and merge with defaults
        if config_path is not None:
            custom_config = self._load_defaults(config_path)

            default_fields = self._get_all_fields(defaults)
            custom_fields = self._get_all_fields(custom_config)

            # Check for new fields not in defaults
            new_fields = custom_fields - default_fields
            if new_fields:
                raise ValueError(
                    f"\nUnexpected field(s) are included in the {self.__class__.__name__} definition:\n"
                    f"   - New field(s): {new_fields}\n"
                    f"   - {self.__class__.__name__} definition: {config_path}\n"
                    f"Please contact the developer to add a new default (see 'defaults/{self.__class__.__name__}.yaml'),\n"
                    f" or remove it from the above {self.__class__.__name__} definition."
                )

            # Merge custom config with defaults (custom values override defaults)
            merged_config = self._merge_configs(defaults, custom_config)
        else:
            merged_config = defaults

        # Dynamically set attributes from all sections in YAML
        for section_name, section_values in merged_config.items():
            if isinstance(section_values, dict):
                for key, value in section_values.items():
                    setattr(self, key, value)
            else:
                # Handle top-level values if any
                setattr(self, section_name, section_values)

    # ------------------------------------------------------------------ #
    #  ORM path                                                            #
    # ------------------------------------------------------------------ #

    def _load_from_orm(self, orm_object: Any) -> None:
        """Copy scalar field values from a Django model instance.

        Only copies fields that exist in the component's defaults so that
        Django-only fields (``id``, ``name``, M2M relations, etc.) are
        silently ignored.  JSONField arrays (lists) are copied as-is.
        """
        defaults = self._load_defaults(None)
        known_fields = self._get_all_fields(defaults)

        for field_name in known_fields:
            if hasattr(orm_object, field_name):
                setattr(self, field_name, getattr(orm_object, field_name))

    @classmethod
    def from_django(cls, orm_object: Any) -> 'ComponentBase':
        """Construct a component instance from a Django ORM model instance.

        Example::

            from dashboard.models import Battery as BatteryModel
            from r2h2.components import Battery

            db_record = BatteryModel.objects.get(pk=1)
            battery   = Battery.from_django(db_record)
            print(battery.rBatteryMWh)

        Args:
            orm_object: A Django model instance.

        Returns:
            An initialised component with attributes populated from the DB.
        """
        return cls(orm_object=orm_object)

    # ------------------------------------------------------------------ #
    #  YAML helpers (unchanged)                                            #
    # ------------------------------------------------------------------ #

    def _load_defaults(self, config_path: Optional[Path] = None) -> dict:
        """Load default parameters from YAML file."""
        if config_path is None:
            class_name = self.__class__.__name__
            config_path = Path(__file__).parent.parent / 'defaults' / f'{class_name}.yaml'

        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    @staticmethod
    def _get_all_fields(config: dict) -> set:
        """Extract all field names from nested config dictionary."""
        fields = set()
        for section_name, section_values in config.items():
            if isinstance(section_values, dict):
                fields.update(section_values.keys())
            else:
                fields.add(section_name)
        return fields

    @staticmethod
    def _merge_configs(defaults: dict, custom: dict) -> dict:
        """Merge custom config with defaults, custom values override defaults."""
        merged = {}

        for section_name, section_values in defaults.items():
            if isinstance(section_values, dict):
                # Initialize section with default values
                merged[section_name] = section_values.copy()

                # Override with custom values if section exists
                if section_name in custom and isinstance(custom[section_name], dict):
                    merged[section_name].update(custom[section_name])
            else:
                # Handle top-level values
                merged[section_name] = custom.get(section_name, section_values)

        return merged
