from django.db import models

#### ---------------------- SIMULATION MODEL (TOP-LEVEL) ---------------------- ####


class Simulation(models.Model):
    name = models.CharField(max_length=100, default='Simulation')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, default='User')  # Placeholder for user association
    # RELATIONSHIPS TO COMPONENT MODELS (MANY-TO-MANY)
    batteries = models.ManyToManyField('Battery', blank=True)
    electro_cells = models.ManyToManyField('ElectroCellPEM', blank=True)
    electrolyser_units = models.ManyToManyField('ElectrolyserUnit', blank=True)
    thermal_properties = models.ManyToManyField('ThermalProperties', blank=True)
    time_outputs = models.ManyToManyField('TimeOutput', blank=True)
    wind_inputs = models.ManyToManyField('WindInput', blank=True)
    # SIMULATION SETTINGS
    iWindType = models.PositiveIntegerField(default=0, choices=[(0, '1 sec'), (1, '1 min'), (2, '10 min'), (3, 'hourly')])
    iNumYears = models.PositiveIntegerField(default=1)
    rTotalTime = models.FloatField(default=3700.0, help_text="Total simulation time in seconds")
    rTimeStep = models.FloatField(default=1.0, help_text="Time step in seconds")
    rTransientSteps = models.PositiveIntegerField(default=101, help_text="Number of initial transient steps to discard in analysis")
    bSingleTurb = models.BooleanField(default=True, help_text="Whether to simulate a single turbine or multiple (weak grid)")
    arLateralDistances = models.JSONField(default=None, blank=True, null=True, help_text="Lateral distances of turbines in weak grid scenario (meters)")
    rDivisor = models.FloatField(default=400.0, help_text="Divisor for normalizing wind power input (e.g. max power of single turbine)")
    duration_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Override simulation duration (days). Truncates wind data to this many days. Leave blank to use the full wind file.')
    datum_date = models.DateField(
        null=True, blank=True,
        help_text='Start date (00:00) used as the datetime axis origin for results charts. Defaults to today if not set.')

    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}"


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
    aiReplacementHour = models.JSONField(default=None, blank=True, null=True)
    # RUNTIME
    rSocAv = models.FloatField(default=0.0)
    rSocMax = models.FloatField(default=0.0)
    rSocMin = models.FloatField(default=0.0)
    rDodAv = models.FloatField(default=0.0)
    arBatteryPower = models.JSONField(default=None, blank=True, null=True)
    arSoC = models.JSONField(default=None, blank=True, null=True)
    arDoD = models.JSONField(default=None, blank=True, null=True)
    # CONTROL
    arBatteryDemand = models.JSONField(default=None, blank=True, null=True)


    def __str__(self):
        return f"ID: {self.id}, Name: {self.name} (MWh: {self.rBatteryMWh})"

    class MetaInfo:
        ui_display_fields = {
            'name':                      'Name',
            'rKt_lc':                    'Kt lc',
            'rKs':                       'Ks',
            'rKT_uc':                    'KT uc',
            'rAlphaSei':                 'Alpha SEI',
            'rKd1':                      'Kd1',
            'rKd2':                      'Kd2',
            'rKd3':                      'Kd3',
            'rBetaSei':                  'Beta SEI',
            'rTcRef':                    'Tc Ref (°C)',
            'rSoCRef':                   'SoC Ref',
            'arInitialSoC':              'Initial SoC',
            'rFt':                       'Ft',
            'rFc':                       'Fc',
            'rBatteryMWh':               'Capacity (MWh)',
            'rInitialBatteryRating':     'Initial Rating (MW)',
            'rBatteryRating':            'Rating (MW)',
            'rRCD':                      'RCD',
            'rControlMinSoC':            'Min SoC',
            'rBatteryProportionalGain':  'Prop. Gain',
            'iNumReplacements':          'Replacements',
            'aiReplacementHour':         'Replacement Hours',
            'rSocAv':                    'SoC Avg',
            'rSocMax':                   'SoC Max',
            'rSocMin':                   'SoC Min',
            'rDodAv':                    'DoD Avg',
            'arBatteryPower':            'Battery Power',
            'arSoC':                     'SoC',
            'arDoD':                     'DoD',
            'arBatteryDemand':           'Battery Demand',
        }


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
    arCurrentDensity = models.JSONField(default=None, blank=True, null=True)
    arE_min = models.JSONField(default=None, blank=True, null=True)
    arR_cell = models.JSONField(default=None, blank=True, null=True)
    arV_cell = models.JSONField(default=None, blank=True, null=True)
    # GEOMETRY & GRID
    iNumCurrent = models.PositiveIntegerField(default=1000)
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

    class MetaInfo:
        ui_display_fields = {
            'name':             'Name',
            'rR':               'Gas Const R (J/mol·K)',
            'rF':               'Faraday Const F (C/mol)',
            'arCurrentDensity': 'Current Density Curve',
            'arE_min':          'E_min Curve',
            'arR_cell':         'R_cell Curve',
            'arV_cell':         'V_cell Curve',
            'iNumCurrent':      'Current Steps',
            'rA_cell':          'Cell Area (cm²)',
            'rI_rated':         'Rated Current Density (A/cm²)',
            'rT_0':             'Nominal Temp (°C)',
            'rT':               'Initial Temp (°C)',
            'rE_min0':          'E_min0 (V)',
            'rR_0':             'R0 (Ω·cm²)',
            'rD_rt':            'dR/dT',
            'rV_cellNom':       'Nominal V_cell (V)',
            'rV_bank':          'Bank Voltage (V)',
            'rI_bank':          'Bank Current (A)',
            'rF1':              'Faraday Eff F1',
            'rF2':              'Faraday Eff F2',
            'arFaradayTemp_C':  'Faraday Temp Points (°C)',
            'arFaradayF1':      'Faraday F1 Points',
            'arFaradayF2':      'Faraday F2 Points',
        }


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
    rRampUp_W_s = models.FloatField(default=None, null=True, blank=True)
    rRampDown_W_s = models.FloatField(default=None, null=True, blank=True)
    # DERIVED
    iNumUnits = models.PositiveIntegerField(default=0)
    rTotalTurnOns = models.FloatField(default=0.0)
    rSummedDegradation = models.FloatField(default=1e-30)
    arDegradationTotal = models.JSONField(default=None, blank=True, null=True)
    # PERFORMANCE_CURVES
    arV_s = models.JSONField(default=None, blank=True, null=True)
    arV_sd = models.JSONField(default=None, blank=True, null=True)
    arI_s = models.JSONField(default=None, blank=True, null=True)
    arH2Dot_s = models.JSONField(default=None, blank=True, null=True)
    arP_Total_s = models.JSONField(default=None, blank=True, null=True)
    arEfficiency_s = models.JSONField(default=None, blank=True, null=True)
    rRatedPower_s = models.FloatField(default=0.0)
    rMinPower_s = models.FloatField(default=0.0)
    rAncilliaryPower_s = models.FloatField(default=0.0)
    # DEGRADATIONS
    arDegradationSteady = models.JSONField(default=None, blank=True, null=True)
    arDegradationFatigue = models.JSONField(default=None, blank=True, null=True)
    arDegradationOnOff = models.JSONField(default=None, blank=True, null=True)
    # TOTALS
    rDegradationOnOffTotal = models.FloatField(default=0.0)
    rDegradationSteadyTotal = models.FloatField(default=0.0)
    rDegradationFatigueTotal = models.FloatField(default=0.0)

    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}, Units: {self.iNumUnits}"

    class MetaInfo:
        ui_display_fields = {
            'name':                      'Name',
            'iN_stacks':                 'Stacks / Bank',
            'iN_banks':                  'Banks / Unit',
            'iNumElectro':               'Num Electrolyser Units',
            'iN_cell':                   'Cells / Stack',
            'iControlLevel':             'Control Level',
            'rTimeConst':                'Time Constant (s)',
            'rDegradation':              'Degradation',
            'rTurnDownRatio':            'Turn-Down Ratio',
            'r_s':                       'r_s',
            'r_f':                       'r_f',
            'r_o':                       'r_o',
            'rAncilliaryPowerFrac':      'Ancillary Power Frac',
            'rDeadBandRatio':            'Dead-Band Ratio',
            'rRampUp_W_s':               'Ramp Up (W/s)',
            'rRampDown_W_s':             'Ramp Down (W/s)',
            'iNumUnits':                 'Total Units',
            'rTotalTurnOns':             'Total Turn-Ons',
            'rSummedDegradation':        'Summed Degradation',
            'arDegradationTotal':        'Degradation Total',
            'arV_s':                     'V_s Curve',
            'arV_sd':                    'V_sd Curve',
            'arI_s':                     'I_s Curve',
            'arH2Dot_s':                 'H2 Rate Curve',
            'arP_Total_s':               'Power Curve',
            'arEfficiency_s':            'Efficiency Curve',
            'rRatedPower_s':             'Rated Power (W)',
            'rMinPower_s':               'Min Power (W)',
            'rAncilliaryPower_s':        'Ancillary Power (W)',
            'arDegradationSteady':       'Degradation Steady',
            'arDegradationFatigue':      'Degradation Fatigue',
            'arDegradationOnOff':        'Degradation On/Off',
            'rDegradationOnOffTotal':    'Deg On/Off Total',
            'rDegradationSteadyTotal':   'Deg Steady Total',
            'rDegradationFatigueTotal':  'Deg Fatigue Total',
        }

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

    class MetaInfo:
        ui_display_fields = {
            'name':          'Name',
            'rAmbientTemp':  'Ambient Temp (°C)',
            'rTauHeating':   'Heating Time Const (s)',
            'rTauCooling':   'Cooling Time Const (s)',
            'rTargetTemp':   'Target Temp (°C)',
            'rMinTemp':      'Min Temp (°C)',
        }

### --------------------- TIME OUTPUT MODEL -------------------- ####

class TimeOutput(models.Model):
    name = models.CharField(max_length=100, default='TimeOutput')
    arTime = models.JSONField(default=None, blank=True, null=True)
    arWindPowerFilt = models.JSONField(default=None, blank=True, null=True)
    arAvailablePower = models.JSONField(default=None, blank=True, null=True)
    arElectroAvailablePowerA = models.JSONField(default=None, blank=True, null=True)
    arElectroAvailablePower = models.JSONField(default=None, blank=True, null=True)
    rPreviousValue = models.FloatField(default=0.0)
    arTotalElectroDemand = models.JSONField(default=None, blank=True, null=True)
    arProportionPower = models.JSONField(default=None, blank=True, null=True)
    aiIsOn = models.JSONField(default=None, blank=True, null=True)
    aiWarmedUp = models.JSONField(default=None, blank=True, null=True)
    aiNumOn = models.JSONField(default=None, blank=True, null=True)
    arTotalElectroOn = models.JSONField(default=None, blank=True, null=True)
    # Unit-level outputs (2D: units x time)
    arElectroDemand = models.JSONField(default=None, blank=True, null=True)
    arI_unit = models.JSONField(default=None, blank=True, null=True)
    arV_unit = models.JSONField(default=None, blank=True, null=True)
    arV_unitUseful = models.JSONField(default=None, blank=True, null=True)
    arPower_unit = models.JSONField(default=None, blank=True, null=True)
    arPower_unitUseful = models.JSONField(default=None, blank=True, null=True)
    arDegradationInEfficiency = models.JSONField(default=None, blank=True, null=True)
    arV_cell = models.JSONField(default=None, blank=True, null=True)
    arProducedH2Dot = models.JSONField(default=None, blank=True, null=True)
    arHydroEfficiency = models.JSONField(default=None, blank=True, null=True)
    # NEW global traces
    arP_el_total = models.JSONField(default=None, blank=True, null=True)
    arT_stack = models.JSONField(default=None, blank=True, null=True)
    arH2Dot_total = models.JSONField(default=None, blank=True, null=True)
    arV_cell_avg = models.JSONField(default=None, blank=True, null=True)
    arEta_el_total = models.JSONField(default=None, blank=True, null=True)
    arEta_system_total = models.JSONField(default=None, blank=True, null=True)
    # NEW per-bank traces
    arP_el_banks = models.JSONField(default=None, blank=True, null=True)     # [num_banks_total, T]
    arT_banks = models.JSONField(default=None, blank=True, null=True)        # [num_banks_total, T]
    # *** NEW: per-stack telemetry ***
    arP_el_unit = models.JSONField(default=None, blank=True, null=True)      # [num_units, T] electrical input per stack (with degradation)
    arQ_gain_unit = models.JSONField(default=None, blank=True, null=True)    # [num_units, T] heat generated per stack = I*(V - V_TN_stack)
    arVtn_unit = models.JSONField(default=None, blank=True, null=True)       # [num_units, T] thermoneutral stack voltage
    arT_unit_bank = models.JSONField(default=None, blank=True, null=True)    # [num_units, T] bank temperature seen by each stack
    # *** NEW: per-bank thermal diagnostics ***
    arQ_gain_banks = models.JSONField(default=None, blank=True, null=True)   # [num_banks_total, T] heat input to each bank
    arQ_lost_banks = models.JSONField(default=None, blank=True, null=True)   # [num_banks_total, T] heat lost to ambient
    arQ_cool_banks = models.JSONField(default=None, blank=True, null=True)   # [num_banks_total, T] heat removed by coolant
    arP_cool_elec_banks = models.JSONField(default=None, blank=True, null=True)  # [num_banks_total, T] electrical power for cooling (COP-based)
    arG_eq_banks = models.JSONField(default =list)     # [num_banks_total, T] equivalent conductance W/K
    arC_th_banks = models.JSONField(default=None, blank=True, null=True)     # [num_banks_total, T] thermal capacitance J/K
    # *** NEW: thermal totals (all banks) ***
    arQ_gain_total = models.JSONField(default=None, blank=True, null=True)   # [T]
    arQ_lost_total = models.JSONField(default=None, blank=True, null=True)   # [T]
    arQ_cool_total = models.JSONField(default=None, blank=True, null=True)   # [T]
    arP_cool_elec_total = models.JSONField(default=None, blank=True, null=True)  # [T]

    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}, Time Steps: {len(self.arTime) if self.arTime else 0}"
    
class WindInput(models.Model):
    name = models.CharField(max_length=100, default='WindInput')
    wind_file = models.FileField(
        upload_to='wind_data/',
        blank=True,
        null=True,
        help_text='HDF5 wind data file (.h5 / .hdf5 / .hdf)',
    )
    arPowerInput = models.JSONField(default=None, blank=True, null=True)
    arTime = models.JSONField(default=None, blank=True, null=True)

    # HDF5 introspection metadata (populated on upload)
    h5_datasets     = models.TextField(blank=True, default='',
                          help_text='Comma-separated list of dataset paths found in the HDF5 file.')
    ts_start        = models.FloatField(null=True, blank=True,
                          help_text='First time value in the per-hour time axis [s].')
    ts_end          = models.FloatField(null=True, blank=True,
                          help_text='Last time value in the per-hour time axis [s].')
    ts_resolution   = models.FloatField(null=True, blank=True,
                          help_text='Time step size [s].')
    ts_n_hours      = models.IntegerField(null=True, blank=True,
                          help_text='Number of hours (columns) in the wind dataset.')

    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}, File: {self.wind_file or '—'}"

    class MetaInfo:
        verbose_name = "Wind Input"
        verbose_name_plural = "Wind Inputs"
        ui_display_fields = {
            'id': 'ID',
            'name': 'Name',
            'wind_file': 'Wind File',
            'ts_start': 'Start Time (s)',
            'ts_end': 'End Time (s)',
            'ts_resolution': 'Time Step (s)',
            'ts_n_hours': 'Number of Hours',
            'arPowerInput': 'Power Input Curve',
            'arTime': 'Time Axis',
            'h5_datasets': 'HDF5 Fields',
        }

#### ---------------------- SIMULATION RUN (JOB TRACKING) ---------------------- ####

class SimulationRun(models.Model):
    PENDING   = 'pending'
    RUNNING   = 'running'
    DONE      = 'done'
    ERROR     = 'error'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (PENDING,   'Pending'),
        (RUNNING,   'Running'),
        (DONE,      'Done'),
        (ERROR,     'Error'),
        (CANCELLED, 'Cancelled'),
    ]

    simulation  = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name='runs')
    status      = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    message     = models.TextField(blank=True, default='')
    description = models.CharField(max_length=200, blank=True, default='',
                                   help_text='Optional user note for this run (up to 200 chars).')
    started_at  = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    output_path = models.CharField(max_length=512, blank=True, default='',
                                   help_text='Relative path (under MEDIA_ROOT/outputs/) to the saved HDF5 results file.')
    xaxis_datetime = models.BooleanField(default=True,
                                         help_text='Display results charts with a datetime x-axis (False = hours index).')

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"Run #{self.id} \u2013 {self.simulation.name} [{self.status}]"

    @property
    def duration_seconds(self):
        """Return elapsed seconds, or None if not finished."""
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def duration_hms(self):
        """Return elapsed time as hh:mm:ss string, or None if not finished."""
        s = self.duration_seconds
        if s is None:
            return None
        total = int(s)
        h, rem = divmod(total, 3600)
        m, sec = divmod(rem, 60)
        return f'{h:02d}:{m:02d}:{sec:02d}'