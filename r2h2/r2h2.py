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
    
    def _get_allowed_classes(self):
        """Dynamically gather allowed classes from initialized components."""
        return [type(getattr(self, attr)).__name__ for attr in dir(self) 
                if hasattr(self, attr) and hasattr(getattr(self, attr), '__class__') 
                and not attr.startswith('_') and attr not in ['paths', 'simulation_name', 'verbose']]
    
    def _safe_instantiate_component(self, class_name, config_path):
        """Safely instantiate a component class without using eval().
        
        Args:
            class_name (str): The name of the component class.
            config_path (Path): Path to the configuration file.
            
        Returns:
            object: An instance of the component class.
            
        Raises:
            ValueError: If the class name is not valid or allowed.
        """
        # Get allowed classes from components module's __all__
        import r2h2.components as components_module
        
        # Use __all__ from components module as the allowed classes
        allowed_classes = getattr(components_module, '__all__', [])
        
        # Fallback to dynamic detection if __all__ is empty
        if not allowed_classes:
            try:
                allowed_classes = self._get_allowed_classes()
            except:
                # Final fallback list
                allowed_classes = ['Simulation', 'Battery', 'ElectroCellPEM', 'ElectrolyserUnit', 
                                 'ThermalProperties', 'TimeOutputs', 'WindInputs']
        
        # Validate class name is allowed
        if class_name not in allowed_classes:
            raise ValueError(f"Invalid class name: {class_name}. Allowed classes: {allowed_classes}")
        
        # Try to get the class from components module first
        if hasattr(components_module, class_name):
            component_class = getattr(components_module, class_name)
            return component_class(config_path=config_path)
        
        # Fallback: try current module (globals)
        if class_name in globals():
            component_class = globals()[class_name]
            return component_class(config_path=config_path)
        
        raise ValueError(f"Class '{class_name}' not found in components module or current namespace")
    
    def __init__(self, simulation_name=None, verbose=False):
        
        self.simulation_name = simulation_name

        # Initialise `r2h2` object with data_root location
        self.verbose = verbose
        self.paths = Paths(verbose=self.verbose)

        self.simulation = Simulation()
        
        # Build components
        for component in self.simulation.components:
            class_name = component['class']
            component_name = component['name']
            target_file = self.paths.data_root / 'component_library' / f'{component_name}.yaml'

            component_instance = self._safe_instantiate_component(
                class_name, 
                target_file
            )
            setattr(self, class_name.lower(), component_instance)


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
        
        # Use the safe instantiation method
        component_instance = self._safe_instantiate_component(
            class_name,
            self.paths.data_root / 'component_library' / f'{component_name}.yaml'
        )
        setattr(self, class_name.lower(), component_instance)

