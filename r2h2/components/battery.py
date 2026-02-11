import yaml
from pathlib import Path
from typing import Optional
import numpy as np

class Battery:
    def __init__(self, config_path: Optional[str] = None):
        
        # Convert config_path to Path object if provided
        if config_path is not None:
            config_path = Path(config_path)
        
        # Load defaults from YAML
        defaults = self._load_defaults(config_path)
        
        # Set attributes from defaults
        self.rKt = defaults['degradation']['rKt']
        self.rKs = defaults['degradation']['rKs']
        self.rKT = defaults['degradation']['rKT']
        self.rAlphaSei = defaults['degradation']['rAlphaSei']
        self.rKd1 = defaults['degradation']['rKd1']
        self.rKd2 = defaults['degradation']['rKd2']
        self.rKd3 = defaults['degradation']['rKd3']
        self.rBetaSei = defaults['degradation']['rBetaSei']
        self.rTcRef = defaults['degradation']['rTcRef']
        self.rSoCRef = defaults['degradation']['rSoCRef']
        
        self.arInitialSoC = defaults['operational']['arInitialSoC']
        self.rFt = defaults['operational']['rFt']
        self.rFc = defaults['operational']['rFc']
        self.rBatteryMWh = defaults['operational']['rBatteryMWh']
        self.rInitialBatteryRating = defaults['operational']['rInitialBatteryRating']
        self.rBatteryRating = defaults['operational']['rBatteryRating']
        self.rRCD = defaults['operational']['rRCD']
        self.rControlMinSoC = defaults['operational']['rControlMinSoC']
        self.rBatteryProportionalGain = defaults['operational']['rBatteryProportionalGain']
        
        self.iNumReplacements = defaults['replacements']['iNumReplacements']
        self.aiReplacementHour = defaults['replacements']['aiReplacementHour']
        
        # runtime computed (initialize to None)
        self.arBatteryPower = None
        self.arSoC = None
        self.arDoD = None
        self.rSocAv = defaults['runtime']['rSocAv']
        self.rSocMax = defaults['runtime']['rSocMax']
        self.rSocMin = defaults['runtime']['rSocMin']
        self.rDodAv = defaults['runtime']['rDodAv']
        
        # control demand (per second)
        self.arBatteryDemand = None
    
    @staticmethod
    def _load_defaults(config_path: Optional[Path] = None) -> dict:
        """Load default battery parameters from YAML file."""
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'defaults' / 'battery.yaml'
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)