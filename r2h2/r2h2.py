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

    


    #######################################################################################
    ###  UI-APP IMPLEMENTATION  ###########################################################
    #######################################################################################
    # WIP - not yet implemented
    def electrolyser(zElectroCell: BaseElectroCell, zElectrolyserUnit: List[ElectrolyserUnit]) -> List[ElectrolyserUnit]:
        """
        Compute per-unit arrays for voltage, current, H2 rate, power, efficiency.
        Mirrors electrolyser() logic with iControlLevel branches.
        """
        # Constants
        # rHhwH2 = 141876.0  # J/g (higher heating value), as used in doc
        rLHV_H2 = 119_988.0  # J/g (33.33 kWh/kg)
        
        rMu = 2.01588      # g/mol
        rF = 9.6485E4      # sA/mol
        rN = 2
        rLossDry = 0.03
        rConstantPart = rMu/rF/rN*(1-rLossDry)

        arCurrentDensity = zElectroCell.arCurrentDensity
        arFaradayEff = zElectroCell.faraday_efficiency(arCurrentDensity)

        for i, e in enumerate(zElectrolyserUnit):
            arV_cell = zElectroCell.arV_cell
            rA_cell = zElectroCell.rA_cell

            if e.iControlLevel == 1:  # Electrolyser level
                arV_s = arV_cell * e.iN_cell * e.iN_stacks * e.iN_banks
                arV_sd = (arV_cell + e.rSummedDegradation) * e.iN_cell * e.iN_stacks * e.iN_banks
                arI_s = arCurrentDensity * rA_cell
                arH2Dot_s = arFaradayEff * rConstantPart * arI_s * e.iN_cell * e.iN_stacks * e.iN_banks
            elif e.iControlLevel == 2:  # Bank level
                arV_s = arV_cell * e.iN_cell * e.iN_stacks
                arV_sd = (arV_cell + e.rSummedDegradation) * e.iN_cell * e.iN_stacks
                arI_s = arCurrentDensity * rA_cell
                arH2Dot_s = arFaradayEff * rConstantPart * arI_s * e.iN_cell * e.iN_stacks
            else:  # Stack level
                arV_s = arV_cell * e.iN_cell
                arV_sd = (arV_cell + e.rSummedDegradation) * e.iN_cell
                arI_s = arCurrentDensity * rA_cell
                arH2Dot_s = arFaradayEff * rConstantPart * arI_s * e.iN_cell

            arP_Total_s = arI_s * arV_sd
            with np.errstate(divide='ignore', invalid='ignore'):
                arEfficiency_s = (rLHV_H2 * arH2Dot_s) / arP_Total_s
                arEfficiency_s = np.nan_to_num(arEfficiency_s, nan=0.0, posinf=0.0, neginf=0.0)

            e.arV_s = arV_s
            e.arV_sd = arV_sd
            e.arI_s = arI_s
            e.arH2Dot_s = arH2Dot_s
            e.arP_Total_s = arP_Total_s
            e.arEfficiency_s = arEfficiency_s
            e.rRatedPower_s = float(arV_s[-1] * arI_s[-1])
            e.rMinPower_s = e.rRatedPower_s * e.rTurnDownRatio
            e.rAncilliaryPower_s = e.rAncilliaryPowerFrac * e.rRatedPower_s

        return zElectrolyserUnit
    
    # WIP - not yet implemented
    def setUpElectro1(zElectrolyserUnit: ElectrolyserUnit, zElectroCell: BaseElectroCell) -> Tuple[List[ElectrolyserUnit], BaseElectroCell]:
        """Initialise the list of electrolyser control units, degradation arrays, and curves."""
        ec = electroCell(zElectroCell)  # uses ec.rT (synced later per bank)
        units: List[ElectrolyserUnit] = [] # DECLARES EMPTY LIST TO BE FILLED, ONLY CONTAINING ELECTROLYSER UNITS
        base = copy.deepcopy(zElectrolyserUnit)
        base.arDegradationTotal = np.zeros(ec.iNumCurrent) + base.rDegradation
        base.rSummedDegradation = 1e-30
        units.append(base)
        # Replicate to iNumUnits
        for _ in range(1, base.iNumUnits):
            e = copy.deepcopy(base)
            e.arDegradationTotal = np.zeros(ec.iNumCurrent) + e.rDegradation
            e.rSummedDegradation = 1e-30
            units.append(e)

        units = electrolyser(ec, units)
        return units, ec
    
    
    # ---  SIMULATION RUN FUNCTION : MIGRATED FROM LEGACY CODE (WIP)  --- #
    def run(self, # PREVIOUSLY: NO `self` ARGUMENT, ALL BELOW WERE PASSED AS FUNCTION ARGUMENTS
        # settings,
        # wind,
        # el_unit,
        # el_cell,
        # battery,
        # kind,
        # use_cooling_feedback,
        # insulated,
        # plot_initial=False
        ):
        
        # import numpy as np
        # import copy
        import time
        
        time.sleep(.1)  # Simulate some startup time
        # Setup electrolyser units and cell
        self.electrolyserunit

        units, ec_curves = setUpElectro1(el_unit, el_cell)  ## THIS SHOULDN'T WORK - WIP
        """

        # Create bank thermal states (one per bank*electrolyser) using tech template
        num_banks_total = el_unit.iN_banks * el_unit.iNumElectro
        th_template = bank_thermal_from_kind(kind, el_unit, insulated=insulated)
        th_banks = [copy.deepcopy(th_template) for _ in range(num_banks_total)]

        # Optional initial plots (keep as in your old structure)
        if plot_initial and plt is not None:
            plt.figure(1)
            for u in units:
                plt.plot(u.arP_Total_s, u.arEfficiency_s, 'k', linewidth=2)
                plt.plot(u.arP_Total_s, 0.8 * u.arEfficiency_s, 'r--', linewidth=2)
            plt.grid(True)
            plt.ylim([0.7 * 0.6244, 0.85])

            plt.figure(2)
            for u in units:
                plt.plot(u.arI_s, u.arV_sd)
            plt.grid(True)
            plt.xlabel("Current [A]")
            plt.ylabel("Voltage [V]")

        num_hours = wind.arPowerInput.shape[1]
        arTotalH2 = np.zeros(num_hours)
        zYearResults = []
        t_out_prev = None

        sim_start_time = time.perf_counter()

        for y in range(settings.iNumYears):
            # Preallocate log arrays
            zLogOut = {
                "arSoc": np.zeros(num_hours),
                "arSocMax": np.zeros(num_hours),
                "arSocMin": np.zeros(num_hours),
                "arSocAv": np.zeros(num_hours),
                "arRCD": np.zeros(num_hours),
                "arBatteryRating": np.zeros(num_hours),
                "arElecOnAv": np.zeros(num_hours),
                "arHourlyDegradation": np.zeros((units[0].iNumUnits, num_hours)),
            }

            for h in range(num_hours):

                if use_cooling_feedback:
                    # First pass: estimate chiller demand without feedback
                    _, t_out_est, _, _ = runElectroStackStep1(
                        ec_curves,
                        copy.deepcopy(th_banks),
                        copy.deepcopy(battery),
                        wind.arPowerInput[:, h],
                        copy.deepcopy(units),
                        wind.arTime,
                        settings,
                        h,
                        t_out_prev,
                        cooling_power_feedback=None,
                    )
                    cooling_feedback = t_out_est.arP_cool_elec_total.copy()

                    # Second pass: enforce chiller power draw on available wind
                    units, t_out, battery, th_banks = runElectroStackStep1(
                        ec_curves,
                        th_banks,
                        battery,
                        wind.arPowerInput[:, h],
                        units,
                        wind.arTime,
                        settings,
                        h,
                        t_out_prev,
                        cooling_power_feedback=cooling_feedback,
                    )
                else:
                    units, t_out, battery, th_banks = runElectroStackStep1(
                        ec_curves,
                        th_banks,
                        battery,
                        wind.arPowerInput[:, h],
                        units,
                        wind.arTime,
                        settings,
                        h,
                        t_out_prev,
                        cooling_power_feedback=None,
                    )

                battery = runBattery1(t_out, battery, settings)

                # Log battery and electrolyser metrics
                zLogOut["arSoc"][h] = battery.arInitialSoC
                zLogOut["arSocMax"][h] = battery.rSocMax
                zLogOut["arSocMin"][h] = battery.rSocMin
                zLogOut["arSocAv"][h] = battery.rSocAv
                zLogOut["arRCD"][h] = battery.rRCD
                zLogOut["arBatteryRating"][h] = battery.rBatteryRating
                zLogOut["arElecOnAv"][h] = float(np.nanmean(t_out.arTotalElectroOn))

                for i in range(units[0].iNumUnits):
                    zLogOut["arHourlyDegradation"][i, h] = units[i].rSummedDegradation

                # Accumulate H2 production
                produced_h2 = np.sum(t_out.arProducedH2Dot)
                arTotalH2[h] = arTotalH2[h - 1] + produced_h2 if h > 0 else produced_h2

                # Carry state forward
                t_out_prev = t_out

            result = {
                "ElectrolyserUnit": copy.deepcopy(units),
                "Battery": copy.deepcopy(battery),
                "ThermalBanks": copy.deepcopy(th_banks),
                "TotalH2": arTotalH2.copy(),
                "Log": zLogOut,
            }
            zYearResults.append(result)

        simulation_runtime_s = time.perf_counter() - sim_start_time

        output = {
            "YearResults": zYearResults,
            "Settings": settings,
            "ElectroCell": el_cell,          # oppure ec_curves se preferisci esportare quello
            "Runtime_s": simulation_runtime_s,
            "Kind": kind,
            "UseCoolingFeedback": use_cooling_feedback,
            "Insulated": insulated,
        }
        """
        output = {'msg': 'Complete'}
        return output
