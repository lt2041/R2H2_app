# README
## Fuel Cell Model

This PEMFC model contains a basic electrochemical model and simulates random on/off results.

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

# Temperature-dependent parameters
# Pressures taken from temperature 80°C
T = 353.15  # K (80°C)
P_H2 = 2.0e5   # Pa
P_O2 = 4.2e4   # Pa
```
These constants are defined once at the beginning of the program to make the code easier to maintain, and
ensures that any changes to physical constants or model parameters only need to be made in one location.
