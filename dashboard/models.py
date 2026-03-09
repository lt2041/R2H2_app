from django.db import models



#### ---------------------- BATTERY MODEL ---------------------- ####

# DB TABLE DEFINITION FOR BATTERY MODEL
class Battery(models.Model):
    name = models.CharField(max_length=100, default='Battery')
    # DEGRADATION
    rKt_lc = models.FloatField(default=4.14e-10)
    rKs = models.FloatField(default=1.04)
    rKT_uc = models.FloatField(default=6.93e-2)
    rAlphaSei = models.FloatField(default=5.75e-2)
    rKd1 = models.FloatField(default=1.4e5)
    rKd2 = models.FloatField(default=-5.01e-1)
    rKd3 = models.FloatField(default=-1.23e5)
    rBetaSei = models.FloatField(default=121.0)
    rTcRef = models.FloatField(default=55.0)
    rSoCRef = models.FloatField(default=0.5)
    # OPERATIONAL
    arInitialSoC = models.FloatField(default=0.5)
    rFt = models.FloatField(default=0.0)
    rFc = models.FloatField(default=0.0)
    rBatteryMWh = models.FloatField(default=15)
    rInitialBatteryRating = models.FloatField(default=0.0)
    rBatteryRating = models.FloatField(default=0.0)
    rRCD = models.FloatField(default=1.0)
    rControlMinSoC = models.FloatField(default=0.5)
    rBatteryProportionalGain = models.FloatField(default=0.0)
    # REPLACEMENTS
    iNumReplacements = models.PositiveIntegerField(default=0)
    aiReplacementHour = models.JSONField(default=list)
    # RUNTIME
    rSocAv = models.FloatField(default=0.0)
    rSocMax = models.FloatField(default=0.0)
    rSocMin = models.FloatField(default=0.0)
    rDodAv = models.FloatField(default=0.0)
    arBatteryPower = models.JSONField(default=list)
    arSoC = models.JSONField(default=list)
    arDoD = models.JSONField(default=list)
    # CONTROL
    arBatteryDemand = models.JSONField(default=list)


    def __str__(self):
        return f"ID: {self.id}, Name: {self.name} (MWh: {self.rBatteryMWh})"
    



#### -------------------- ELECTROCELL MODEL -------------------- ####

# DEFAULTS FOR JSON FIELDS (must be functions to avoid mutable default argument issues)
def default_faraday_temp():
    return [40.0, 60.0, 80.0]

def default_faraday_f1():
    return [150.0, 200.0, 250.0]

def default_faraday_f2():
    return [0.99, 0.985, 0.98]

# DB TABLE DEFINITION FOR ELECTROCELL MODEL
class ElectroCellPEM(models.Model):
    name = models.CharField(max_length=100, default='ElectroCellPEM')
    # UNIVERSAL CONSTANTS
    rR = models.FloatField(default=8.314)
    rF = models.FloatField(default=96485.0)
    # OUTPUTS POPULATED BY BUILD_CURVES()
    arCurrentDensity = models.JSONField(default=list)
    arE_min = models.JSONField(default=list)
    arR_cell = models.JSONField(default=list)
    arV_cell = models.JSONField(default=list)
    # GEOMETRY & GRID
    iNumCurrent = models.FloatField(default=1000)
    rA_cell = models.FloatField(default=1000.0, help_text="cm^2")
    rI_rated = models.FloatField(default=3.0, help_text="A/cm^2")
    # TEMPERATURE REFERENCES
    rT_0 = models.FloatField(default=55.0, help_text="Nominal operating temperature [°C]")
    rT = models.FloatField(default=55.0, help_text="Initial operating temperature [°C]")
    # PEM VOLTAGE MODEL PARAMS
    rE_min0 = models.FloatField(default=1.55)
    rR_0 = models.FloatField(default=0.178, help_text="should be x2 according to literature but polarization curve would be too steep")
    rD_rt = models.FloatField(default=-0.0045 , help_text="dR/dT")
    # STACK/CELL NOMINALS (INFORMATIVE)
    rV_cellNom = models.FloatField(default=2.1)
    rV_bank = models.FloatField(default=633.5)
    rI_bank = models.FloatField(default=3000.0)
    # FARADAY EFF PARAMS
    rF1 = models.FloatField(default=0.25)
    rF2 = models.FloatField(default=0.996)
    arFaradayTemp_C = models.JSONField(default=default_faraday_temp)
    arFaradayF1 = models.JSONField(default=default_faraday_f1)
    arFaradayF2 = models.JSONField(default=default_faraday_f2)
    
    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}"



### -------------------- ELECTROLYSER UNIT MODEL -------------------- ####

class ElectrolyserUnit(models.Model):
    name = models.CharField(max_length=100, default='ElectrolyserUnit')
    # TOPOLOGY
    iN_stacks = models.PositiveIntegerField(default=0)
    iN_banks = models.PositiveIntegerField(default=0)
    iNumElectro = models.PositiveIntegerField(default=0)
    iN_cell = models.PositiveIntegerField(default=0)
    iControlLevel = models.PositiveIntegerField(default=2, choices=[(1, 'Electrolyser'), (2, 'Bank'), (3, 'Stack')])
    # DYNAMICS
    rTimeConst = models.FloatField(default=30.0)
    rDegradation = models.FloatField(default=1e-30)
    rTurnDownRatio = models.FloatField(default=0.125)
    r_s = models.FloatField(default=1.42e-10)
    r_f = models.FloatField(default=3.33e-7)
    r_o = models.FloatField(default=1.47e-4)
    rAncilliaryPowerFrac = models.FloatField(default=0.0, help_text="Always required (For WT and all - set to zero for weak grid rather than off gid)")
    rDeadBandRatio = models.FloatField(default=2.0)
    # RAMP_LIMITS
    rRampUp_W_s = models.FloatField(default=None)
    rRampDown_W_s = models.FloatField(default=None)
    # DERIVED
    iNumUnits = models.PositiveIntegerField(default=0)
    rTotalTurnOns = models.FloatField(default=0.0)
    rSummedDegradation = models.FloatField(default=1e-30)
    arDegradationTotal = models.JSONField(default=list)
    # PERFORMANCE_CURVES
    arV_s = models.JSONField(default=list)
    arV_sd = models.JSONField(default=list)
    arI_s = models.JSONField(default=list)
    arH2Dot_s = models.JSONField(default=list)
    arP_Total_s = models.JSONField(default=list)
    arEfficiency_s = models.JSONField(default=list)
    rRatedPower_s = models.FloatField(default=0.0)
    rMinPower_s = models.FloatField(default=0.0)
    rAncilliaryPower_s = models.FloatField(default=0.0)
    # DEGRADATIONS
    arDegradationSteady = models.JSONField(default=list)
    arDegradationFatigue = models.JSONField(default=list)
    arDegradationOnOff = models.JSONField(default=list)
    # TOTALS
    rDegradationOnOffTotal = models.FloatField(default=0.0)
    rDegradationSteadyTotal = models.FloatField(default=0.0)
    rDegradationFatigueTotal = models.FloatField(default=0.0)

    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}, Units: {self.iNumUnits}"
    

### -------------------- THERMAL PROPERTIES MODEL -------------------- ####

class ThermalProperties(models.Model):
    name = models.CharField(max_length=100, default='ThermalProperties')
    rAmbientTemp = models.FloatField(default=15.0)
    rTauHeating = models.FloatField(default=120.0, help_text="Time constant for heating (seconds)")
    rTauCooling = models.FloatField(default=180.0, help_text="Time constant for cooling (seconds)")
    rTargetTemp = models.FloatField(default=60.0, help_text="Target operating temperature (°C)")
    rMinTemp = models.FloatField(default=50.0, help_text="Minimum operating temperature (°C)")
 
    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}, Target Temp: {self.rTargetTemp}°C"
    

### --------------------- TIME OUTPUT MODEL -------------------- ####

class TimeOutput(models.Model):
    name = models.CharField(max_length=100, default='TimeOutput')
    arTime = models.JSONField(default=list)
    arWindPowerFilt = models.JSONField(default=list)
    arAvailablePower = models.JSONField(default=list)
    arElectroAvailablePowerA = models.JSONField(default=list)
    arElectroAvailablePower = models.JSONField(default=list)
    rPreviousValue = models.FloatField(default=0.0)
    arTotalElectroDemand = models.JSONField(default=list)
    arProportionPower = models.JSONField(default=list)
    aiIsOn = models.JSONField(default=list)
    aiWarmedUp = models.JSONField(default=list)
    aiNumOn = models.JSONField(default=list)
    arTotalElectroOn = models.JSONField(default=list)
    # Unit-level outputs (2D: units x time)
    arElectroDemand = models.JSONField(default=list)
    arI_unit = models.JSONField(default=list)
    arV_unit = models.JSONField(default=list)
    arV_unitUseful = models.JSONField(default=list)
    arPower_unit = models.JSONField(default=list)
    arPower_unitUseful = models.JSONField(default=list)
    arDegradationInEfficiency = models.JSONField(default=list)
    arV_cell = models.JSONField(default=list)
    arProducedH2Dot = models.JSONField(default=list)
    arHydroEfficiency = models.JSONField(default=list)
    # NEW global traces
    arP_el_total = models.JSONField(default=list)
    arT_stack = models.JSONField(default=list)
    arH2Dot_total = models.JSONField(default=list)
    arV_cell_avg = models.JSONField(default=list)
    arEta_el_total = models.JSONField(default=list)
    arEta_system_total = models.JSONField(default=list)
    # NEW per-bank traces
    arP_el_banks = models.JSONField(default=list)     # [num_banks_total, T]
    arT_banks = models.JSONField(default=list)        # [num_banks_total, T]
    # *** NEW: per-stack telemetry ***
    arP_el_unit = models.JSONField(default=list)      # [num_units, T] electrical input per stack (with degradation)
    arQ_gain_unit = models.JSONField(default=list)    # [num_units, T] heat generated per stack = I*(V - V_TN_stack)
    arVtn_unit = models.JSONField(default=list)       # [num_units, T] thermoneutral stack voltage
    arT_unit_bank = models.JSONField(default=list)    # [num_units, T] bank temperature seen by each stack
    # *** NEW: per-bank thermal diagnostics ***
    arQ_gain_banks = models.JSONField(default=list)   # [num_banks_total, T] heat input to each bank
    arQ_lost_banks = models.JSONField(default=list)   # [num_banks_total, T] heat lost to ambient
    arQ_cool_banks = models.JSONField(default=list)   # [num_banks_total, T] heat removed by coolant
    arP_cool_elec_banks = models.JSONField(default=list)  # [num_banks_total, T] electrical power for cooling (COP-based)
    arG_eq_banks = models.JSONField(default =list)     # [num_banks_total, T] equivalent conductance W/K
    arC_th_banks = models.JSONField(default=list)     # [num_banks_total, T] thermal capacitance J/K
    # *** NEW: thermal totals (all banks) ***
    arQ_gain_total = models.JSONField(default=list)   # [T]
    arQ_lost_total = models.JSONField(default=list)   # [T]
    arQ_cool_total = models.JSONField(default=list)   # [T]
    arP_cool_elec_total = models.JSONField(default=list)  # [T]

    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}, Time Steps: {len(self.arTime)}"
    
class WindInput(models.Model):
    name = models.CharField(max_length=100, default='WindInput')
    arPowerInput = models.JSONField(default=list)
    arTime = models.JSONField(default=list)

    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}, Time Steps: {len(self.arTime)}"