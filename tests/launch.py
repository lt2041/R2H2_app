# %% Import package

import r2h2


# %% Initialise R2H2 object (finds data path, builds components)

sim = r2h2.go()


# %% Examine simulation parameters (the output is converted to a dictionary at display-time, for easier reading)
vars(sim.simulation)

# %% Examine component parameters (the output is converted to a dictionary at display-time, for easier reading)

vars(sim.battery)
vars(sim.electrolyser_unit)
vars(sim.thermal_properties)
vars(sim.wind_inputs)
vars(sim.electro_cell_pem)
# %%

sim.update_battery() # This will fail due to naming in user-defined components folder (e.g. `Battery-1.yaml`) - WIP
vars(sim.battery)

# %%
sim.electro_cell_pem.build_curves()