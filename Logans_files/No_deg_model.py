
"""
V1.0 - Initial commit for 160kW model with no degradation code. 
V1.0.1 - Added physical constants and operating conditions as global variables.
V1.0.2 - Changed simulation to hours instead of minutes. Total H2 usage in tons, total energy generation in MWh.
V1.0.3 - Added month separation and degradation description.
V1.0.4 - Fixed formatting of outputs

V1.1.0 - Changed outputs and table to match R2H2 (power against time instead of current density against time).
V1.1.1 - Added simple degradation values with sources, lacking source for k_cycle. FC Controller code to be added.
V1.1.2 - Added simple controller model for degradation implementation. 
"""

import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# PHYSICAL CONSTANTS
# ============================================================

# --- Physical / thermodynamic constants ---
GAS_CONSTANT = 8.314           # J/(mol·K)
FARADAY_CONSTANT = 96485.0     # C/mol
H2_MOLAR_MASS = 0.002016       # kg/mol
H2_LHV_KWH_PER_KG = 33.33      # kWh/kg, lower heating value of hydrogen

# --- Electrochemical constants ---
GIBBS_FREE_ENERGY = -237.13e3  # J/mol, Gibbs free energy of formation for water at standard conditions
NUM_ELECTRONS = 2              # number of electrons transferred per H2 molecule in the reaction

# --- Model-specific coefficients ---
# These coefficients are derived from empirical data and literature for PEM fuel cells.
BETA_1 = -0.948                # Activation overpotential coefficient
BETA_2 = 2.86e-3               # Temperature coefficient for activation overpotential
BETA_3 = 2.0e-4                # Concentration coefficient for activation overpotential
BETA_4 = 7.6e-5                # Current density coefficient for activation overpotential


# ============================================================
# FUEL CELL OPERATING CONDITIONS
# ============================================================

# --- Temperature-dependent parameters ---
# Pressures taken from operation at 80°C
T = 353.15       # K (80°C)
P_H2 = 3e5       # Pa
P_O2 = 2.5e5     # Pa
P_H2O = 4.74e4   # Pa

# --- Fuel cell stack parameters ---
CELL_AREA_CM2 = 500.0          # cm²
CELL_RESISTANCE = 0.1          # ohm·cm²
RATED_CURRENT_DENSITY = 1.41   # A/cm²
MAX_CURRENT_DENSITY = 2.1      # A/cm²
NUM_CELLS = 336
RATED_STACK_POWER_KW = 160.0   # Rated power in kW
NUM_CURRENT_POINTS = 1000      # resolution of the polarisation curve


# ============================================================
# RANDOM STEP SIMULATION SETTINGS
# ============================================================

# --- Simulation configuration ---
SIM_DT = 0.1                                  # time step in hours
SIM_T_END = 3600.0                            # total simulation time in hours
TAU_VALUES = np.arange(0.4, 0.8 + 0.01, 0.4)  # smoothing time constants to test
TAUS_TO_PLOT = [0.8, 1.6, 2.4, 3.2]           # specific tau values for plotting
V_LOAD_LIMIT = 0.1                            # A/cm² per hour, maximum rate of change of current density
N_TRANSITIONS = 500                           # number of random transitions in the commanded profile
TRANSITION_MIN_DT = 20.0                      # minimum duration of each transition in hours
TRANSITION_MAX_DT = 60.0                      # maximum duration of each transition in hours
TRANSITION_MAX_DJ = 0.6                       # maximum change in current density per transition


# ============================================================
# ELECTROCHEMICAL MODEL EQUATIONS
# ============================================================

def calc_concentration(P, T):
    C_m3 = P / (8.314 * T)
    return C_m3 / 1e6  # mol/m³ → mol/cm³

# Nernst Equation
def calc_V_nernst(T, P_H2, P_O2):
    return (-GIBBS_FREE_ENERGY / (NUM_ELECTRONS * FARADAY_CONSTANT)
            + GAS_CONSTANT * T / (NUM_ELECTRONS * FARADAY_CONSTANT)
            * np.log(P_H2 * np.sqrt(P_O2) / P_H2O))

# Activation Loss
def calc_V_act(T, c_O2, J):
    return -(BETA_1 + (BETA_2 * T) + BETA_3 * T * np.log(c_O2) - (BETA_4 * T * np.log(J)))

# Ohmic Loss
def calc_V_ohm(R_cell, J):
    return R_cell * J

# Concentration Loss
def calc_V_conc(T, J, J_max):
    return -(GAS_CONSTANT * T / (NUM_ELECTRONS * FARADAY_CONSTANT)
            * np.log(1 - (J / J_max)))


# ============================================================
# PEM FUEL CELL CLASS
# ============================================================

class FuelCellPEM:

    def __init__(self):
        # Operating parameters
        self.iNumCurrent = NUM_CURRENT_POINTS
        self.rI_rated = RATED_CURRENT_DENSITY  # A/cm²
        self.rI_max = MAX_CURRENT_DENSITY      # A/cm²
        self.rT = T                            # 353.15K (80°C),
        self.rR_cell = CELL_RESISTANCE         # ohm·cm²
        self.P_H2 = P_H2                       # Pa
        self.P_O2 = P_O2                       # Pa

        # Stack configuration
        self.area_cm2 = CELL_AREA_CM2          # active area per cell
        self.n_cells = NUM_CELLS        

        # Arrays to be filled by build_curves()
        self.arCurrentDensity = None
        self.arV_cell = None
        self.arP_density = None

        # Max power point 
        self.J_maxP = None
        self.V_maxP = None
        self.Pd_maxP = None

        # --------------------------------------------------------
        # Degradation coefficients (see README for full sourcing/assumptions)
        # --------------------------------------------------------
        self.k_steady = 4e-6         # V/h operating [https://www.sciencedirect.com/science/article/pii/S0378775301010291]
        self.k_cycle = 1e-3         # V per unit Σ|ΔJ| — placeholder, unsourced
        self.k_startstop = 33.8e-6   # V per start/stop event, 100% RH [https://www.sciencedirect.com/science/article/pii/S0360319910003356]
        self.k_highload = 1.14e-3    # V/h above high-load threshold [https://www.sciencedirect.com/science/article/pii/S0016236125000687]

        self.rSummedDegradation = 1e-30  # persistent running total (V) (avoids divide by zero error)


    # --------------------------------------------------------
    # Build polarisation curve
    # --------------------------------------------------------
    def build_curves(self):
        J = np.linspace(0.001, self.rI_max * 0.999, self.iNumCurrent)
        T = self.rT

        c_H2 = calc_concentration(self.P_H2, T)
        c_O2 = calc_concentration(self.P_O2, T)

        V_nernst = calc_V_nernst(T, self.P_H2, self.P_O2)
        V_act = calc_V_act(T, c_O2, J)
        V_ohm = calc_V_ohm(self.rR_cell, J)
        V_conc = calc_V_conc(T, J, self.rI_max)

        V_cell = V_nernst - V_act - V_ohm - V_conc
        P_density = V_cell * J

        self.arCurrentDensity = J
        self.arV_cell = V_cell
        self.arP_density = P_density

        idx = np.argmax(P_density)
        self.J_maxP = J[idx]
        self.V_maxP = V_cell[idx]
        self.Pd_maxP = P_density[idx]
        self.P_rated_kW = RATED_STACK_POWER_KW

        return self


    # --------------------------------------------------------
    # Interpolate voltage
    # --------------------------------------------------------
    def get_voltage(self, J_query):
        return np.interp(J_query, self.arCurrentDensity, self.arV_cell)


    # --------------------------------------------------------
    # Stack-level I–V–P
    # --------------------------------------------------------
    def stack_IV(self, I_stack):
        J = I_stack / self.area_cm2
        V_cell = self.get_voltage(J)
        V_stack = V_cell * self.n_cells
        P_stack = V_stack * I_stack
        return V_stack, P_stack


    # --------------------------------------------------------
    # Hydrogen consumption
    # --------------------------------------------------------
    def h2_consumption(self, I_stack, utilisation=1.0):
        if I_stack <= 0:
            return 0.0, 0.0

        n_dot = (I_stack * self.n_cells) / (2 * FARADAY_CONSTANT * utilisation)
        m_dot = n_dot * H2_MOLAR_MASS
        return n_dot, m_dot


    # --------------------------------------------------------
    # Efficiency calculation
    # --------------------------------------------------------
    def fc_efficiency(self, energy_kWh, total_H2_used):
        return energy_kWh / (total_H2_used * H2_LHV_KWH_PER_KG) if total_H2_used > 0 else 0.0


# =========================================================
# RANDOM STEP SIMULATION FUNCTIONS
# =========================================================

    # --------------------------------------------------------
    # Loading-rate limiter
    # --------------------------------------------------------
    def ramp_current_density(self, J_cmd, J_actual, dt, v_load):
        dJ = J_cmd - J_actual
        max_step = v_load * dt
        dJ_limited = np.clip(dJ, -max_step, max_step)
        J_new = J_actual + dJ_limited
        return np.clip(J_new, 0.0, self.rI_rated)  # Ensure J stays within bounds


    # --------------------------------------------------------
    # Smooth tanh transition
    # --------------------------------------------------------
    def smooth_step(self, t, t_start, dt_load, J_ini, J_step):
        mid = t_start + dt_load / 2
        scale = dt_load / 2
        return J_ini + (J_step - J_ini) * (1 + np.tanh((t - mid) / scale)) / 2
        

    # --------------------------------------------------------
    # Smoothing first-order curve
    # --------------------------------------------------------
    def first_order_smooth(self, x_cmd, x_prev, tau, dt):
        return x_prev + (dt / tau) * (x_cmd - x_prev)


    # --------------------------------------------------------
    # Multi-step current profile
    # --------------------------------------------------------
    def current_profile(self, t, transitions, J0=0.0):
        J = J0
        for tr in transitions:
            mid = tr["t_start"] + tr["dt_load"] / 2
            scale = tr["dt_load"] / 2
            J += tr["dJ"] * (1 + np.tanh(4 * (t - mid) / scale)) / 2
        return J


    # --------------------------------------------------------
    # Controller: rate-limit + smooth a commanded profile,
    # tracking cumulative degradation per stressor at every step
    # (mirrors R2H2's per-step arDegradationSteady/Fatigue/OnOff arrays)
    # --------------------------------------------------------
    def run_controller(self, J_cmd, dt, tau, v_load,
                        J_idle_threshold=0.01, J_highload_threshold=1.5,
                        degradation_start=None):
        """
        degradation_start: optional dict {'steady','cycle','startstop','highload'}
        giving cumulative totals (V) to continue from — lets multiple runs be
        chained end-to-end (e.g. day-by-day) instead of resetting to zero each
        call. Defaults to a fresh stack.
        """
        n = len(J_cmd)
        J_actual = np.zeros(n)
        J_now = 0.0
        was_on = False

        if degradation_start is None:
            degradation_start = {"steady": 0.0, "cycle": 0.0, "startstop": 0.0, "highload": 0.0}

        arDegradationSteady = np.zeros(n)
        arDegradationCycle = np.zeros(n)
        arDegradationStartstop = np.zeros(n)
        arDegradationHighload = np.zeros(n)

        running_steady = degradation_start["steady"]
        running_cycle = degradation_start["cycle"]
        running_startstop = degradation_start["startstop"]
        running_highload = degradation_start["highload"]

        for i in range(n):
            J_limited = self.ramp_current_density(J_cmd[i], J_now, dt, v_load)
            J_prev = J_now
            J_now = self.first_order_smooth(J_limited, J_prev, tau, dt)
            J_actual[i] = J_now

            is_on = J_now > J_idle_threshold

            running_steady += self.k_steady * dt if is_on else 0.0
            running_cycle += self.k_cycle * abs(J_now - J_prev)
            running_startstop += self.k_startstop if (is_on and not was_on) else 0.0
            running_highload += self.k_highload * dt if J_now >= J_highload_threshold else 0.0
            was_on = is_on

            arDegradationSteady[i] = running_steady
            arDegradationCycle[i] = running_cycle
            arDegradationStartstop[i] = running_startstop
            arDegradationHighload[i] = running_highload

        arDegradationTotal = (arDegradationSteady + arDegradationCycle
                               + arDegradationStartstop + arDegradationHighload)

        self.rSummedDegradation = arDegradationTotal[-1] + 1e-30 if n > 0 else 1e-30

        degradation = {
            "steady": arDegradationSteady,
            "cycle": arDegradationCycle,
            "startstop": arDegradationStartstop,
            "highload": arDegradationHighload,
            "total": arDegradationTotal,
        }

        return J_actual, degradation




def generate_random_transitions(n_steps=20, 
                            J_min=0.0, J_max=RATED_CURRENT_DENSITY,
                            max_dJ=0.6,
                            min_dt=5.0, max_dt=25.0):
        
    transitions = []
    t = 0.0
    J_now = 0.0

    for _ in range(n_steps):
        # Random step up or down
        dJ = np.random.uniform(-max_dJ, max_dJ)

        # Keep within bounds
        if J_now + dJ > J_max:
            dJ = J_max - J_now
        if J_now + dJ < J_min:
            dJ = J_min - J_now

        dt_load = np.random.uniform(min_dt, max_dt)

        transitions.append({
            "dJ": dJ,
            "t_start": t,
            "dt_load": dt_load
        })

        J_now += dJ
        t += dt_load

    return transitions

    # Plot

def build_raw_transition_profile(transitions, dt=0.1, t_end=3600):
    time = np.arange(0, t_end, dt)
    J = np.zeros_like(time)

    J_now = 0.0
    idx = 0

    for tr in transitions:
        t_start = tr["t_start"]
        t_end_tr = tr["t_start"] + tr["dt_load"]

        # Apply dJ at t_start
        while idx < len(time) and time[idx] < t_start:
            J[idx] = J_now
            idx += 1

        J_now += tr["dJ"]

        while idx < len(time) and time[idx] < t_end_tr:
            J[idx] = J_now
            idx += 1

    # Fill remaining time
    while idx < len(time):
        J[idx] = J_now
        idx += 1

    return time, J

# --------------------------------------------------------
# Graph Polarisation Curve Function
# --------------------------------------------------------
def plot_polarisation_curves(cell):
    plt.figure(figsize=(8,6))

    plt.plot(
        cell.arCurrentDensity,
        cell.arV_cell,
        linewidth=2,
        label=f"{cell.rT-273.15:.0f}°C"
    )

    plt.xlabel("Current Density (A/cm²)")
    plt.ylabel("Cell Voltage (V)")
    plt.title("PEMFC Polarisation Curves")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

# --------------------------------------------------------
# Graph Power Density Curve Function
# --------------------------------------------------------
def plot_power_density_curve(cell):
    plt.figure(figsize=(8,6))
    plt.plot(
        cell.arCurrentDensity,
        cell.arP_density,
        linewidth=2,
        label=f"{cell.rT-273.15:.0f}°C"
    )
    plt.xlabel("Current Density (A/cm²)")
    plt.ylabel("Power Density (W/cm²)")
    plt.title("PEMFC Power Density Curve")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()




# ============================================================
# MAIN SIMULATION
# ============================================================

def main():
    cell = FuelCellPEM()
    cell.build_curves()

    #plot_polarisation_curves(cell)
    #plot_power_density_curve(cell)

    tau_values = np.arange(0.1, 0.4 + 0.0001, 0.05)

    transitions = generate_random_transitions(n_steps=500)

    time_raw, J_raw = build_raw_transition_profile(transitions, dt=0.1, t_end=3600)

    # ============================================================
    # PLOT RAW + SMOOTHED PROFILES FOR tau values
    # ============================================================

    taus_to_plot = [0.1]
    dt = 0.1
    v_load = 0.2

    I_stack_raw = J_raw * cell.area_cm2
    P_raw_kW = np.array([min(cell.stack_IV(I)[1] / 1000, cell.P_rated_kW) for I in I_stack_raw])

    plt.figure(figsize=(50, 10))
    plt.plot(time_raw, P_raw_kW, label="Raw (no smoothing)", color="black", linewidth=2)

    for tau in taus_to_plot:
        J_smooth, _ = cell.run_controller(J_raw, dt, tau, v_load)

        I_stack_smooth = J_smooth * cell.area_cm2
        P_smooth_kW = np.array([min(cell.stack_IV(I)[1] / 1000, cell.P_rated_kW) for I in I_stack_smooth])

        plt.plot(time_raw, P_smooth_kW, label=f"Smoothed (tau={tau})")

    plt.title("Raw vs Smoothed Power")
    plt.xlabel("Time (h)")
    plt.ylabel("Power (kW)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    print(f"{'Tau':>5} | {'H2 Used (t)':>12} | {'Energy (MWh)':>14} | "
        f"{'kWh/kg of H2':>12} | {'Δ(kWh/kg)':>12} | {'Eff (%)':>10} | {'Degradation (µV)':>17}")
    print("-" * 105)

    prev_kWh_per_kg = None

    for tau in tau_values:

        dt = 0.1
        t_end = 3600.0
        time = np.arange(0, t_end, dt)

        # commanded profile
        J_cmd = np.array([cell.current_profile(t, transitions) for t in time])
        J_cmd = np.clip(J_cmd, 0.0, cell.J_maxP)

        # rate limiter + smoothing + degradation tracking
        v_load = 0.2
        J_actual, degradation = cell.run_controller(J_cmd, dt, tau, v_load)

        # stack calculations
        I_stack = J_actual * cell.area_cm2
        V_stack = np.zeros_like(time)
        P_stack = np.zeros_like(time)
        H2_flow = np.zeros_like(time)

        for i in range(len(time)):
            V, P = cell.stack_IV(I_stack[i])
            V_stack[i] = V
            P_kW = P / 1000
            P_stack[i] = min(P_kW, cell.P_rated_kW)
            _, mH2 = cell.h2_consumption(I_stack[i])
            H2_flow[i] = mH2 * 3600.0  # kg/hr

        energy_kWh = np.cumsum(P_stack * dt)  # kWh
        energy_MWh = energy_kWh / 1000.0  # MWh

        total_H2_used_kg = np.sum(H2_flow) * dt # kg
        total_H2_used_ton = total_H2_used_kg / 1000.0  # t
        total_energy_kWh = energy_kWh[-1]
        total_energy_MWh = energy_MWh[-1]

        eff = cell.fc_efficiency(total_energy_kWh, total_H2_used_kg)
        eff_pct = round(eff * 100, 2)

        kWh_per_kg = total_energy_kWh / total_H2_used_kg if total_H2_used_kg > 0 else 0.0

        if prev_kWh_per_kg is None:
            delta = 0.0
        else:
            delta = kWh_per_kg - prev_kWh_per_kg

        prev_kWh_per_kg = kWh_per_kg

        degradation_uV = degradation["total"][-1] * 1e6

        print(f"{tau:5.2f} | {total_H2_used_ton:12.4f} | {total_energy_MWh:14.4f} | "
              f"{kWh_per_kg:12.4f} | {delta:12.4f} | {eff_pct:10.2f} | {degradation_uV:17.3f}")

main()
