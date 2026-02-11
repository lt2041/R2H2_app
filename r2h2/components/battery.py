import yaml
from pathlib import Path
from typing import Optional

class Battery:
    def __init__(self, config_path: Optional[str] = None):
        
        # Convert config_path to Path object if provided
        if config_path is not None:
            config_path = Path(config_path)
        
        # Load defaults from YAML
        defaults = self._load_defaults(config_path)
        
        # If custom config provided, validate against defaults
        if config_path is not None:
            default_fields = self._get_all_fields(self._load_defaults(None))
            custom_fields = self._get_all_fields(defaults)
            
            # Check for new fields not in defaults
            new_fields = custom_fields - default_fields
            if new_fields:
                raise ValueError(
                    f"\nUnexpected field(s) are included in the battery definition:\n"
                    f"   - New field(s): {new_fields}\n"
                    f"   - Battery definition: {config_path}\n"
                    f"Please contact the developer to add a new default (see 'defaults/battery.yaml'),\n or remove it from the above battery definition."
                )
        
        # Dynamically set attributes from all sections in YAML
        for section_name, section_values in defaults.items():
            if isinstance(section_values, dict):
                for key, value in section_values.items():
                    setattr(self, key, value)
            else:
                # Handle top-level values if any
                setattr(self, section_name, section_values)
    
    @staticmethod
    def _load_defaults(config_path: Optional[Path] = None) -> dict:
        """Load default battery parameters from YAML file."""
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'defaults' / 'battery.yaml'
        
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