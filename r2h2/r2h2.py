#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###############################################################################################################
# Standard Python Libraries
import os
import socket
from pathlib import Path

# Custom Libraries
from .config import Paths
from .components import Battery

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
    
    

    # ---  UPDATE FUNCTIONS TO RE-LOAD PARAMETERS FROM YAML FILES  --- #

    def update_battery(self):
        """Load battery parameters from a YAML file."""
        self.battery = Battery(config_path=self.paths.inputs / 'battery.yaml')

