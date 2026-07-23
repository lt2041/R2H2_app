# README
## Fuel Cell Model

This PEMFC model contains a basic electrochemical model and simulates random on/off results.

In this version, the model is configurated using pre-defined variables that can be edited directly within the Python source file.
As a result, any changes to model parameters or operating conditions must be made at the code level before running the simulation.



---

## Electrochemical Model
The electrochemical model is based on the equations given in Montazerinejad et al. The equations from Table 1 used are shown below:

$$
(5) \quad V_{\mathrm{FC}} = E_{\mathrm{Nernst}} - V_{\mathrm{act}} - V_{\mathrm{ohm}} - V_{\mathrm{conc}}
$$

(5) represents the **overall PEMFC cell voltage equation** for the model.

<br>

### Nernst Equation

$$
(1) \quad E_{\mathrm{Nernst}} = \frac{-\Delta G^\circ}{n_{e}F} + \frac{RT_{FC}}{n_{e}F} ln\left(\frac{P_{H_{2}}\sqrt{P_{O_{2}}}}{P^{\mathrm{Sat}}_{H_2O}}\right)
$$


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

```
# --- Physical / thermodynamic constants ---
GAS_CONSTANT = 8.314  # J/(mol·K)
FARADAY_CONSTANT = 96485.0  # C/mol
H2_MOLAR_MASS = 0.002016  # kg/mol

# --- Temperature-dependent parameters ---
# Pressures taken from temperature 80°C
T = 353.15  # K (80°C)
P_H2 = 2.0e5   # Pa
P_O2 = 4.2e4   # Pa

# --- Fuel cell stack parameters ---
CELL_AREA_CM2 = 500.0  # cm²
CELL_RESISTANCE = 0.178  # ohm·cm²
RATED_CURRENT_DENSITY = 1.41  # A/cm²
```
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

---

## Degradation
*Degradation modeling to be implemented*

## On/Off Simulation
On/Off simulation is randomly... *(TBC, to organise code first)*



## Documentation

- Montazerinejad et al. https://www.sciencedirect.com/science/article/pii/S0196890424008859
