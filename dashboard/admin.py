from django.contrib import admin
from .models import *


admin.site.register(Battery)
admin.site.register(ElectroCellPEM)
admin.site.register(ElectrolyserUnit)
admin.site.register(ThermalProperties)
admin.site.register(TimeOutput)
admin.site.register(WindInput)
admin.site.register(Simulation)