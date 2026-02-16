import numpy as np
from abc import ABC, abstractmethod

from .base import ComponentBase

class BaseElectroCell(ABC):
    """
    Common interface for electrolyzer cell types.
    Subclasses must implement build_curves() and faraday_efficiency().
    Arrays are defined after build_curves().
    """

    @abstractmethod
    def build_curves(self) -> "BaseElectroCell":
        ...

    @abstractmethod
    def faraday_efficiency(self, J: np.ndarray) -> np.ndarray:
        ...


# Bind all methods from ComponentBase to abstract BaseElectroCell (generic component functionality, yaml loading, etc.)
BaseElectroCell.__init__ = ComponentBase.__init__
BaseElectroCell._load_defaults = ComponentBase._load_defaults
BaseElectroCell._get_all_fields = ComponentBase._get_all_fields
BaseElectroCell._merge_configs = ComponentBase._merge_configs


class ElectroCellPEM(BaseElectroCell):
    
    def build_curves(self) -> "ElectroCellPEM":
        ec = self
        J = np.linspace(0.0, ec.rI_rated, ec.iNumCurrent)
        T_stack = ec.rT
        E_min = ec.rE_min0 + (ec.rR * (273.15 + T_stack)) / (2.0 * ec.rF)
        R_cell = (T_stack - ec.rT_0) * ec.rD_rt + ec.rR_0
        V_cell = E_min - E_min * np.exp(-250.0 * J) + R_cell * J

        ec.arCurrentDensity = J
        ec.arE_min = np.full_like(J, E_min)
        ec.arR_cell = np.full_like(J, R_cell)
        ec.arV_cell = V_cell
        return ec

    def faraday_efficiency(self, J: np.ndarray) -> np.ndarray:
        return (J**2 / (self.rF1 + J**2)) * self.rF2
