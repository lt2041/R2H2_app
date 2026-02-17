# %% Import package

import r2h2


# %% Initialise R2H2 object (finds data path, builds components)

sim = r2h2.go()


# %% Examine component parameters (the output is converted to a dictionary at display-time, for easier reading)

sim.battery.__dict__
sim.electrolyser_unit.__dict__
sim.thermal_properties.__dict__
sim.wind_inputs.__dict__
sim.electro_cell_pem.__dict__
# %%

sim.update_battery()
sim.battery.__dict__

# %%
sim.electro_cell_pem.build_curves()