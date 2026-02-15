#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###############################################################################################################
# Standard Python Libraries
import os
import socket
from pathlib import Path


# Custom Libraries
from r2h2.config import Paths
from r2h2.components import Battery, ElectrolyserUnit, ThermalProperties

###############################################################################################################


# R2H2 main class
class R2H2():
    # Gather simulation parameters from system environment variables
    
    def __init__(self, simulation_name=None, verbose=False):
        
        self.simulation_name = simulation_name

        # Initialise `r2h2` object with data_root location
        self.verbose = verbose
        self.paths = Paths(verbose=self.verbose)
        
        
        # Bulid components
        self.battery = Battery()
        self.electrolyser_unit = ElectrolyserUnit()
        self.thermal_properties = ThermalProperties()
    
    

    # ---  UPDATE FUNCTIONS TO RE-LOAD PARAMETERS FROM YAML FILES  --- #

    def update_battery(self):
        """Load battery parameters from a YAML file."""
        self.battery = Battery(config_path=self.paths.inputs / 'Battery.yaml')

    def update_electrolyser_unit(self):
        """Load electrolyser unit parameters from a YAML file."""
        self.electrolyser_unit = ElectrolyserUnit(config_path=self.paths.inputs / 'ElectrolyserUnit.yaml')

    def update_thermal_properties(self):
        """Load thermal properties parameters from a YAML file."""
        self.thermal_properties = ThermalProperties(config_path=self.paths.inputs / 'ThermalProperties.yaml')