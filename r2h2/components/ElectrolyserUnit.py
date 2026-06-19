import math
from .base import ComponentBase


class ElectrolyserUnit(ComponentBase):
    """Electrolyser unit topology, dynamics and degradation tracking."""

    def __init__(self, orm_object=None):
        # Topology (overwritten by apply_unit_topology at runtime)
        self.iN_stacks    = 4
        self.iN_banks     = 2
        self.iNumElectro  = 5
        self.iN_cell      = 0
        self.iControlLevel = 2   # 1=Electrolyser, 2=Bank, 3=Stack
        # Dynamics
        self.rTimeConst          = 0.0
        self.rDegradation        = 1e-30
        self.rTurnDownRatio      = 0.125
        self.r_s                 = 1.42e-10
        self.r_f                 = 3.33e-7
        self.r_o                 = 1.47e-4
        self.rAncillaryPowerFrac = 0.0
        self.rDeadBandRatio      = 2.0
        # Ramp limits (None = unlimited)
        self.rRampUp_W_s   = None
        self.rRampDown_W_s = None
        # Derived
        self.iNumUnits           = 0
        self.rTotalTurnOns       = 0
        self.rSummedDegradation  = 1e-30
        self.arDegradationTotal  = None
        # Performance curves
        self.arV_s           = None
        self.arV_sd          = None
        self.arI_s           = None
        self.arH2Dot_s       = None
        self.arP_Total_s     = None
        self.arEfficiency_s  = None
        self.rRatedPower_s   = 0.0
        self.rMinPower_s     = 0.0
        self.rAncillaryPower_s = 0.0
        # Degradation history
        self.arDegradationSteady  = None
        self.arDegradationFatigue = None
        self.arDegradationOnOff   = None
        # Totals
        self.rDegradationOnOffTotal   = 0.0
        self.rDegradationSteadyTotal  = 0.0
        self.rDegradationFatigueTotal = 0.0

        super().__init__(orm_object=orm_object)
