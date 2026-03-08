# `initialise_simulation`

> This should be defined in top-level `r2h2` class, with settings sub-module

This is a function within `renew2h2.py`, stack as follows:
- `Settings` class
    - high-level parameters, includes turbine array separation distances
-  `single-turb` boolean 
    - sent as argument to `initialise_simulation` - forces array separation distances to empty array
- `ElectrolyserUnit` class is called, then specialised to 'ALK' using `apply_unit_topology`
- `apply_unit_topology` then calls `_preset_section` which refers to a static structure defining defaults for Electrolyser, specifically targetting the 'topology' sub-dict
    - can be steam-rolled with new default/yaml framework
    - `ElectrolyserUnit` goes into and out-of `apply_unit_topology` so could have been a bound function, but may be irrelevant if new approach to defaults is used and all of this code is removed
- `el.iControlLevel` set to 2 (bank) - hard-coded. 
    - This seems to be managed as a default already, so line may be redundant
    - `el.iControlLevel` seems to simply re-scale certain values up/down to adjust focus on electrolyser/bank/stacks - only appears as a conditional, changing how elements are divided/multiplied but nbanks/nstacks
- `Battery()` class is called - equivalent to new definition
- Segment on battery scalling seems partially redundant with too many fields:
    ```
    bat.rInitialBatteryRating = bat.rBatteryMWh * 3.6e9
    bat.rBatteryRating = bat.rInitialBatteryRating
    bat.rBatteryProportionalGain = bat.rInitialBatteryRating / 3600.0 / 10e6
    ```
- `ThermalProperties()` class is called - equivalent to new definition