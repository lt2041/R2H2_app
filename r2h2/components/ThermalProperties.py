from .base import ComponentBase


class ThermalProperties(ComponentBase):
    """Thermal model parameters for electrolyser banks."""

    def __init__(self, orm_object=None):
        self.rAmbientTemp  = 15.0
        self.rTauHeating   = 1200.0   # 20 * 60 s
        self.rTauCooling   = 1800.0   # 30 * 60 s
        self.rTargetTemp   = 60.0
        self.rMinTemp      = 50.0

        super().__init__(orm_object=orm_object)
