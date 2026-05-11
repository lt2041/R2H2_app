from django.contrib import admin
from .models import *


@admin.register(Controller)
class ControllerAdmin(admin.ModelAdmin):
    list_display  = ('name', 'filename', 'author', 'date_created', 'verified', '_edit_count')
    list_filter   = ('verified', 'date_created')
    search_fields = ('name', 'file', 'author', 'description')
    readonly_fields = ('date_created', 'edit_history')
    fieldsets = (
        (None, {
            'fields': ('name', 'file', 'description'),
        }),
        ('Provenance', {
            'fields': ('author', 'date_created', 'verified'),
        }),
        ('Edit History', {
            'classes': ('collapse',),
            'fields': ('edit_history',),
        }),
    )

    @admin.display(description='Edits')
    def _edit_count(self, obj):
        h = obj.edit_history
        return len(h) if isinstance(h, list) else 0


admin.site.register(Battery)
admin.site.register(ElectroCellPEM)
admin.site.register(ElectrolyserUnit)
admin.site.register(ThermalProperties)
admin.site.register(TimeOutput)
admin.site.register(WindInput)
admin.site.register(Simulation)
admin.site.register(SimulationRun)