#!/usr/bin/env python3
# -*- coding: utf-8 -*-




###############################################################################################################
# Standard Python Libraries
import os
import socket
from pathlib import Path

# Custom Libraries
from .config import get_or_create_config

###############################################################################################################



# R2H2 class to hold paths and other global settings
class Paths():

    def __init__(self, verbose=True):

        # Initialise `R2H2` object with data_root location
        cfg = get_or_create_config()
        self.data_root = Path(cfg['paths']['data_root'])
        self.inputs = self.data_root / 'inputs'
        self.outputs = self.data_root / 'outputs'
        self.simulation_defs = self.data_root / 'simulation_defs'
        
        # Determine whether Windows or Unix
        if os.name == 'nt':
            self.machine_id = "Windows"
        else:
            self.machine_id = socket.gethostname()
        
        # Prompt user on data_root location and how to change it
        if verbose:
            print(f"R2H2 is configured to access data stored here: {self.data_root}.")
            print(f'To change this path, use:  r2h2.config.update_data_root("{str(Path.home() / "...")}")\n')

# ------------------------------------------------------------------------------------------------------------

# R2H2 main class
class R2H2():
    # Gather simulation parameters from system environment variables
    
    def __init__(self, simulation_name=None, verbose=False):
        
        self.simulation_name = simulation_name

        # Initialise `r2h2` object with data_root location
        self.verbose = verbose
        self.paths = Paths(verbose=self.verbose)

