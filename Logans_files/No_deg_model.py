
"""
V1.0 - Initial commit for 160kW model with no degradation code. 
"""

import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# SUPPORTING EQUATIONS
# ============================================================

def calc_concentration(P, T):
    C_m3 = P / (8.314 * T)
    return C_m3 / 1e6  # mol/m³ → mol/cm³

def calc_V_nernst(T, p_h2, p_o2):
    return 1.229 - 0.85e-5 * (T - 298.15) + 4.31e-5 * T * (np.log(p_h2) + 0.5 * np.log(p_o2))

def calc_V_act(T, c_o2, i):
    return -(-0.948 + (2.86e-3 * T) + (2.0e-4 * T * np.log(c_o2)) - (7.6e-5 * T * np.log(i)))

def calc_V_ohm(R_cell, J):
    return R_cell * J

def calc_V_conc(T, J, J_max):
    return -(4.308e-5 * T) * np.log(1 - (J / J_max))

# ============================================================
# PEM FUEL CELL CLASS
# ============================================================

class FuelCellPEM:

    def __init__(self):
        # Operating parameters
        self.iNumCurrent = 1000
        self.rI_rated = 1.41         # A/cm²
        self.rT = 353.15             # K (80°C),
        self.rR_cell = 0.178         # ohm·cm², slightly off from literature (same as Adam's model)
        self.p_h2 = 2.0e5            # Pa
        self.p_o2 = 4.2e4            # Pa

        # Stack configuration
        self.area_cm2 = 500.0    # active area per cell,
        self.n_cells = 336        #

        # Arrays to be filled
        self.arCurrentDensity = None
        self.arV_cell = None
        self.arP_density = None

        # Max power point
        self.J_maxP = None
        self.V_maxP = None
        self.Pd_maxP = None

    # --------------------------------------------------------
    # Build polarisation curve
    # --------------------------------------------------------
    def build_curves(self):
        J = np.linspace(0.001, self.rI_rated, self.iNumCurrent)
        T = self.rT

        c_h2 = calc_concentration(self.p_h2, T)
        c_o2 = calc_concentration(self.p_o2, T)

        V_nernst = calc_V_nernst(T, self.p_h2, self.p_o2)
        V_act = calc_V_act(T, c_o2, J)
        V_ohm = calc_V_ohm(self.rR_cell, J)
        V_conc = calc_V_conc(T, J, self.rI_rated)

        V_cell = V_nernst - V_act - V_ohm - V_conc
        P_density = V_cell * J

        self.arCurrentDensity = J
        self.arV_cell = V_cell
        self.arP_density = P_density

        idx = np.argmax(P_density)
        self.J_maxP = J[idx]
        self.V_maxP = V_cell[idx]
        self.Pd_maxP = P_density[idx]
        self.P_rated_kW = 160.0  # Rated power in kW

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

        F = 96485.0
        M_H2 = 0.002016
        n_dot = (I_stack * self.n_cells) / (2 * F * utilisation)
        m_dot = n_dot * M_H2
        return n_dot, m_dot

    # --------------------------------------------------------
    # Efficiency calculation
    # --------------------------------------------------------
    def fc_efficiency(self, energy_kWh, total_H2_used):
        return energy_kWh / (total_H2_used * 33.33) if total_H2_used > 0 else 0.0

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
        return J_ini + (J_step - J_ini) * (1 + np.tanh(4 * (t - mid) / scale)) / 2
        
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

def generate_random_transitions(n_steps=20, 
                            J_min=0.0, J_max=1.41,
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


    # ============================================================
    # MAIN SIMULATION
    # ============================================================

def main():
    cell = FuelCellPEM()
    cell.build_curves()

    tau_values = np.arange(0.4, 0.8 + 0.0001, 0.1)

    print(f"{'Tau':>5} | {'H2 Used (kg)':>12} | {'Energy (kWh)':>14} | "
          f"{'kWh/kg H2':>12} | {'Δ(kWh/kg)':>12}")
    print("-" * 70)

    transitions = generate_random_transitions(n_steps=500)

    time_raw, J_raw = build_raw_transition_profile(transitions, dt=0.1, t_end=3600)
    #plt.figure(figsize=(20, 10))
    #plt.plot(time_raw, J_raw, color="black")
    #plt.title("Raw Transition Profile (No Smoothing)")
    #plt.xlabel("Time (s)")
    #plt.ylabel("Commanded J (A/cm²)")
    #plt.grid(True)
    #plt.show()

    # ============================================================
    # PLOT RAW + SMOOTHED PROFILES FOR tau values
    # ============================================================

    taus_to_plot = [0.4, 0.6, 0.8]
    dt = 0.1
    v_load = 0.2

    plt.figure(figsize=(50, 10))
    plt.plot(time_raw, J_raw, label="Raw (no smoothing)", color="black", linewidth=2)

    for tau in taus_to_plot:
        J_smooth = np.zeros_like(time_raw)
        J_now = 0.0

        for i, t in enumerate(time_raw):
            # rate limit first
            J_limited = cell.ramp_current_density(J_raw[i], J_now, dt, v_load)
            # then smooth
            J_now = cell.first_order_smooth(J_limited, J_now, tau, dt)
            J_smooth[i] = J_now

        plt.plot(time_raw, J_smooth, label=f"Smoothed (tau={tau})")

    plt.title("Raw vs Smoothed Current Density Profiles")
    plt.xlabel("Time (s)")
    plt.ylabel("Current Density J (A/cm²)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    prev_kWh_per_kg = None

    for tau in tau_values:

        dt = 0.1
        t_end = 3600.0
        time = np.arange(0, t_end, dt)

        # commanded profile
        J_cmd = np.array([cell.current_profile(t, transitions) for t in time])
        J_cmd = np.clip(J_cmd, 0.0, cell.J_maxP)

        # rate limiter + smoothing
        v_load = 0.2
        J_actual = np.zeros_like(time)
        J_now = 0.0

        for i, t in enumerate(time):
            J_limited = cell.ramp_current_density(J_cmd[i], J_now, dt, v_load)
            J_now = cell.first_order_smooth(J_limited, J_now, tau, dt)
            J_actual[i] = J_now

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

        energy_kJ = np.cumsum(P_stack * dt)
        energy_kWh = energy_kJ / 3600.0

        total_H2_used = np.sum(H2_flow / 3600) * dt
        total_energy = energy_kWh[-1]

        eff = cell.fc_efficiency(total_energy, total_H2_used)
        print(f"Tau: {tau:.2f}, Efficiency: {eff*100:.2f}%")

        kWh_per_kg = total_energy / total_H2_used if total_H2_used > 0 else 0.0

        if prev_kWh_per_kg is None:
            delta = 0.0
        else:
            delta = kWh_per_kg - prev_kWh_per_kg

        prev_kWh_per_kg = kWh_per_kg

        print(f"{tau:5.2f} | {total_H2_used:12.4f} | {total_energy:14.4f} | "
              f"{kWh_per_kg:12.4f} | {delta:12.4f}")

main()
