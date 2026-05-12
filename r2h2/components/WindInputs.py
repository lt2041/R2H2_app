from .base import ComponentBase


class WindInputs(ComponentBase):
    """Wind power input data container."""

    def __init__(self, orm_object=None):
        self.arPowerInput = None   # shape (time_steps, num_hours)
        self.arTime       = None   # 1-D time vector (seconds)

        super().__init__(orm_object=orm_object)
