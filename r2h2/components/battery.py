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