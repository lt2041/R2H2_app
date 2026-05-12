from typing import Any

class ComponentBase:
    """
    Base class for all components in R2H2.
    Subclasses define their own defaults as Python attributes in __init__.
    Supports optional initialisation from a Django ORM model instance.
    """

    def __init__(self, orm_object: Any = None):
        """
        Initialise component.

        Args:
            orm_object: Optional Django model instance.  When provided, field
                        values are copied onto this instance, overriding the
                        subclass defaults.
        """
        if orm_object is not None:
            self._load_from_orm(orm_object)

    # ------------------------------------------------------------------ #
    #  ORM path                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _coerce_numeric(value: Any) -> Any:
        """Convert string values that represent numbers to int or float."""
        if not isinstance(value, str):
            return value
        v = value.strip()
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            pass
        return value

    def _load_from_orm(self, orm_object: Any) -> None:
        """Copy scalar field values from a Django model instance.

        Only copies fields that exist in the component's defaults so that
        Django-only fields (``id``, ``name``, M2M relations, etc.) are
        silently ignored.  JSONField arrays (lists) are copied as-is.
        """
        defaults = self._load_defaults(None)
        known_fields = self._get_all_fields(defaults)

        for field_name in known_fields:
            if hasattr(orm_object, field_name):
                setattr(self, field_name, getattr(orm_object, field_name))

    @classmethod
    def from_django(cls, orm_object: Any) -> 'ComponentBase':
        """Construct a component instance from a Django ORM model instance.

        Example::

            from dashboard.models import Battery as BatteryModel
            from r2h2.components import Battery

            db_record = BatteryModel.objects.get(pk=1)
            battery   = Battery.from_django(db_record)
            print(battery.rBatteryMWh)

        Args:
            orm_object: A Django model instance.

        Returns:
            An initialised component with attributes populated from the DB.
        """
        return cls(orm_object=orm_object)

