# Simulation settings container — no YAML file required.

class Simulation:
    """Lightweight container for simulation-level settings.

    All attributes are initialised from Python defaults; no YAML file is read.
    Values are overwritten at runtime by :meth:`R2H2.__init__` and
    :meth:`R2H2.map_to_db_objects` from the Django DB Simulation record.
    """

    def __init__(self):
        # Simulation timing
        self.iWindType        = 0      # 0=1 s, 1=1 min, 2=10 min, 3=hourly
        self.iNumYears        = 1
        self.rTotalTime       = 3700   # seconds
        self.rTimeStep        = 1.0
        self.rTransientSteps  = 101

        # Wind / turbine
        self.bSingleTurb          = False
        self.arLateralDistances   = [504, 1008, 1512, 2016, 2520]

        # Control divisor (overwritten after topology is resolved)
        self.rDivisor = 1.0
