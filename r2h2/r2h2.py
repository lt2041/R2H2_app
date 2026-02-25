#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###############################################################################################################
# Standard Python Libraries
import os
import socket
from pathlib import Path
import sys


# Custom Libraries
from r2h2.config import Paths
from r2h2.components import *

###############################################################################################################


# R2H2 main class
class R2H2():
    # Gather simulation parameters from system environment variables
    
    def __init__(self, simulation_name=None, verbose=False):
        
        self.simulation_name = simulation_name

        # Initialise `r2h2` object with data_root location
        self.verbose = verbose
        self.paths = Paths(verbose=self.verbose)

        self.simulation = Simulation()
        
        # Build components
        self.battery = Battery()
        self.electro_cell_pem = ElectroCellPEM()
        self.electrolyser_unit = ElectrolyserUnit()
        self.thermal_properties = ThermalProperties()
        self.time_outputs = TimeOutputs()
        self.wind_inputs = WindInputs()


    # ---  GENERIC UPDATE FUNCTION TO RE-LOAD PARAMETERS FROM YAML FILES  --- #

    def update_component(self, class_name=None, component_name=None):
        """Load component parameters from a YAML file.
        
        Args:
            class_name (str): The name of the component class to update (e.g. `Battery`).
            component_name (str): The name of the component YAML file to load (e.g. `Battery-0.yaml`).
        
        Usage examples:
            sim.update_component(class_name='Battery', component_name='Battery-0.yaml')
            sim.update_component(class_name='ElectrolyserUnit', component_name='ElectrolyserUnit-1.yaml')
        """
        
        # Raise errors if class name or component name are not provided
        if class_name is None:
            raise KeyError("Please provide a class name to update (e.g. `Battery`).")
        if component_name is None:
            raise KeyError("Please provide a component name to update (e.g. `Battery-0.yaml`).")
        
        # Ensure extension is removed from component name (e.g. `Battery-0.yaml` -> `Battery-0`)
        component_name = component_name.replace('.yaml', '').replace('.yml', '')
        
        # Dynamically gather allowed classes from initialized components
        allowed_classes = [type(getattr(self, attr)).__name__ for attr in dir(self) 
                          if hasattr(self, attr) and hasattr(getattr(self, attr), '__class__') 
                          and not attr.startswith('_') and attr not in ['paths', 'simulation_name', 'verbose']]
        
        # Safe access to classes using `getattr` and `hasattr` to avoid potential security issues with `eval`
        current_module = sys.modules[__name__]

        if hasattr(current_module, class_name) and class_name in allowed_classes:
            component_class = getattr(current_module, class_name)
            setattr(self, class_name.lower(), component_class(config_path=self.paths.data_root / 'component_library' / f'{component_name}.yaml'))
        else:
            raise ValueError(f"Invalid class name: {class_name}")

