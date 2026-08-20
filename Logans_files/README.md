# README

## Proton Exchange Membrane (PEM) Fuel Cell Model

This PEMFC model contains a basic, 0D electrochemical model and simulates random on/off results.

In this version, the model is configured using pre-defined variables that can be edited directly within the Python source file.
As a result, any changes to model parameters or operating conditions must be made at the code level before running the simulation.
This version is ran and tested through a Jupyter notebook file (*.ipynb*).

More information on how to use Jupyter Notebooks in VS Code: https://code.visualstudio.com/docs/datascience/jupyter-notebooks

For any further questions, please contact me at *lt2041@hw.ac.uk*.

---
## Assumptions 
This model assumes the fuel cell operates at 80°C (353.15K) which directly affects the pressure values.
- `P_H2`, `P_O2` and `P_H2O` are fixed values of pressures at 80°C and will be different at other temperatures. <TBC, confirm values!>

Degradation constants vary under operating conditions in different studies.
- `k_startstop` is taken at 100% relative humidity<sup>[1]</sup>.
- `k_cycle` is unsourced, and is replaced with a placeholder value of `1e-3` to be 3 orders of magnitude greater than `k_steady`, to closer align with R2H2's electrolyser.

## Code Clarifications
- `1e-30` is used in multiple cases to avoid the program running into 'divide by zero' errors. It does not affect the program, as it is so minut.
- `0.999` is used to build the polarisation curve to avoid a 'divide by zero' error.
- `P_H2O` is currently unused.

## Electrochemical Model
The electrochemical model is based on the equations given in Montazerinejad et al<sup>[4]</sup>. The equations from Table 1 used are shown below:

$$
(5) \quad V_{\mathrm{FC}} = E_{\mathrm{Nernst}} - V_{\mathrm{act}} - V_{\mathrm{ohm}} - V_{\mathrm{conc}}
$$

(5) represents the **overall PEMFC cell voltage equation** for the model.

<br>

### Nernst Equation

$$
(1) \quad E_{\mathrm{Nernst}} = \frac{-\Delta G^\circ}{n_{e}F} + \frac{RT_{FC}}{n_{e}F} ln\left(\frac{P_{H_{2}}\sqrt{P_{O_{2}}}}{P^{\mathrm{Sat}}_{H_2O}}\right)
$$

Concentration is..... (calculated by ... to be finished)


### Activation Loss

$$
(6) \quad V_{act} = \beta_{1} + \beta_{2}T_{FC} + \beta_{3}T_{FC}lnC_{O_{2,conc}} + \beta_{4}T_{FC}ln(I)
$$


### Ohmic Loss

$$
(7) \quad V_{ohm} = IR_{int}
$$


### Concentration Loss

$$
(8) \quad V_{conc} = \frac{RT_{FC}}{n_{e}F} ln\left(\frac{i_{L}}{i_{L}-i}\right)
$$

---

All constants and pre-defined variables used in this model are written in Screaming Snake Case at the top of the file. For example:


> **Physical / thermodynamic constants**
> ```
> GAS_CONSTANT = 8.314  # J/(mol·K)
> FARADAY_CONSTANT = 96485.0  # C/mol
> H2_MOLAR_MASS = 0.002016  # kg/mol
> ```

> **Temperature-dependent parameters,**
> **pressures taken from temperature 80°C**
> ```
> T = 353.15  # K (80°C)
> P_H2 = 2.0e5   # Pa
> P_O2 = 4.2e4   # Pa
> ```

> **Fuel cell stack parameters**
> ```
> CELL_AREA_CM2 = 500.0  # cm²
> CELL_RESISTANCE = 0.178  # ohm·cm²
> RATED_CURRENT_DENSITY = 1.41  # A/cm²
> ```

These constants are defined once at the beginning of the program to make the code easier to maintain, and
ensures that any changes to physical constants or model parameters only need to be made in one location.

---

## Efficiency and Consumption
### Efficiency
The efficiency of the PEMFC is calculated using the LHV-based fuel cell efficiency equation:

$$
\eta_{FC} = \frac{E_{out}}{m_{H_{2}}LHV_{H_{2}}}
$$

### Consumption
Hydrogen consumption and energy output is calculated using:

$$
\dot{n}_{H_2} = \frac{I_{stack}N_{cells}}{2F\,U}
$$

$$
\dot{m}_{H_2} = \dot{n}_{H_2}M_{H_{2}}
$$

- `n_dot` is the **molar flow rate of hydrogen** (mol/s)
- `m_dot` is the **mass flow rate of hydrogen** (kg/s)

Hydrogen is assumed to carry no loss of gas. For example, for every 1kg of hydrogen in, 1kg will be used by the fuel cell.
- `utilisation=1.0` within the h2_consumption function. This can be changed accordingly.

---

## Degradation
This degradation model estimates cumulative cell voltage loss using a linear combination of four independent cases derived from literature.

$$
\Delta V = k_{steady} \cdot t_{operating} + k_{cycle} \cdot \sum|\Delta J| + k_{startstop} \cdot N_{startstop} + k_{highload} \cdot t_{abovethreshold}
$$

- **Steady decay** - baseline voltage loss accumulated from continuous operation, applied per hour the stack is running.
- **Cycle decay** - voltage loss from load-following stress, applied per unit of cumulative current density change.
- **Start-stop decay** - voltage loss from cathode carbon corrosion during on/off transitions, applied per start-stop event.
- **High load decay** - voltage loss from mass-transport and thermal stress at high current density, applied per hour spent above the set threshold.

The constants (k values) vary throughout studies depending on operating conditions and other factors.
- `k_steady = 4e-6`<sup>[1]</sup>
- `k_startstop = 33.8e-6`<sup>[2]</sup>
- `k_highload = 1.14e-3`<sup>[3]</sup>

---

## Random Step Simulation
The Random Step simulation ....

---

## Results
When ran in a Junyper notebook, the polarisation curve and power density are generated.
- Polarisation Curve: Cell voltage against current density - creates point at rated current density.
- Power Density Curve: Power density against current density - creates point at rated and peak power density.

A graph of random transitions, raw vs smoothed, is also generated. The random transitions are discussed in the "Random Step Simulation" section above.

Final results are printed as a table:
- Tau: value of tau used in the random step smoothing
- H2 Used (t): tons of hydrogen used by the fuel cell
- Energy (MWh): Megawatt-hours generated from the fuel cell
- kWh/kg of H2 (MWh): Amount of energy generated per kg of hydrogen
- Δ(kWh/kg): Change in kwh/kg from previous value of Tau *(always 0.0 if only one value of Tau is tested)*
- Eff (%): Efficiency of the fuel cell
- Degradation (µV): Degradation of the cell voltage in microvolts.


## Documentation

- Fowler et al. https://www.sciencedirect.com/science/article/pii/S0378775301010291 [k_steady = 4e-6]
- Seo et al. https://www.sciencedirect.com/science/article/pii/S0360319910003356 [k_startstop = 33.8e-6]
- Ge et al. https://www.sciencedirect.com/science/article/pii/S0016236125000687 [k_highload = 1.14e-3]
- Montazerinejad et al. https://www.sciencedirect.com/science/article/pii/S0196890424008859 
