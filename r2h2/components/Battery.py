from .base import ComponentBase


class Battery(ComponentBase):
    """Battery component with degradation and SoC tracking."""

    def __init__(self, orm_object=None):
        # Degradation
        self.rKt         = 4.14e-10
        self.rKs         = 1.04
        self.rKT         = 6.93e-2
        self.rAlphaSei   = 5.75e-2
        self.rKd1        = 1.4e5
        self.rKd2        = -5.01e-1
        self.rKd3        = -1.23e5
        self.rBetaSei    = 121.0
        self.rTcRef      = 55.0
        self.rSoCRef     = 0.5
        # Operational
        self.arInitialSoC           = 0.5
        self.rFt                    = 0.0
        self.rFc                    = 0.0
        self.rBatteryMWh            = 15.0
        self.rInitialBatteryRating  = 0.0
        self.rBatteryRating         = 0.0
        self.rRCD                   = 1.0
        self.rControlTargetSoC      = 0.5
        self.rBatteryProportionalGain = 0.0
        # Replacements
        self.iNumReplacements  = 0
        self.aiReplacementHour = None
        # Runtime
        self.rSocAv        = 0.0
        self.rSocMax       = 0.0
        self.rSocMin       = 0.0
        self.rDodAv        = 0.0
        self.arBatteryPower = None
        self.arSoC          = None
        self.arDoD          = None
        # Control
        self.arBatteryDemand = None

        super().__init__(orm_object=orm_object)
