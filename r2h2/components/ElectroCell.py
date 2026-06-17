import numpy as np
from .base import ComponentBase


class ElectroCellPEM(ComponentBase):
    """PEM electrolyser cell electrochemistry model."""

    def __init__(self, orm_object=None):
        # Universal constants
        self.rR = 8.314
        self.rF = 96485.0
        # Outputs populated by build_curves()
        self.arCurrentDensity = None
        self.arE_min          = None
        self.arR_cell         = None
        self.arV_cell         = None
        # Geometry & grid
        self.iNumCurrent = 1000
        self.rA_cell     = 1000.0   # cm^2
        self.rI_rated    = 3.0      # A/cm^2
        # Temperature references
        self.rT_0 = 20.0   # Nominal operating temperature [°C]
        self.rT   = 55.0   # Initial operating temperature [°C]
        # PEM voltage model
        self.rE_min0 = 1.55
        self.rR_0    = 0.178   # Ω·cm²
        self.rD_rt   = -0.0045  # dR/dT
        # Stack/cell nominals (informative)
        self.rV_cellNom = 2.1
        self.rV_bank    = 633.5
        self.rI_bank    = 3000.0
        # Faraday efficiency
        self.rF1 = 0.25
        self.rF2 = 0.996
        self.arFaradayTemp_C = [40.0, 60.0, 80.0]
        self.arFaradayF1     = [150.0, 200.0, 250.0]
        self.arFaradayF2     = [0.99, 0.985, 0.98]

        super().__init__(orm_object=orm_object)

    def build_curves(self) -> "ElectroCellPEM":
        ec = self
        J = np.linspace(0.0, ec.rI_rated, ec.iNumCurrent)
        T_stack = ec.rT
        E_min = ec.rE_min0 + (ec.rR * (273.15 + T_stack)) / (2.0 * ec.rF)
        R_cell = (T_stack - ec.rT_0) * ec.rD_rt + ec.rR_0
        V_cell = E_min - E_min * np.exp(-250.0 * J) + R_cell * J

        ec.arCurrentDensity = J
        ec.arE_min  = np.full_like(J, E_min)
        ec.arR_cell = np.full_like(J, R_cell)
        ec.arV_cell = V_cell
        return ec

    def faraday_efficiency(self, J: np.ndarray) -> np.ndarray:
        return (J**2 / (self.rF1 + J**2)) * self.rF2
