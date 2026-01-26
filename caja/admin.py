from django.contrib import admin
from .models import CierreCaja


@admin.register(CierreCaja)
class CierreCajaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'usuario',
        'empresa',
        'fecha_apertura',
        'fecha_cierre',
        'estado',
        'efectivo_sistema',
        'efectivo_real',
        'diferencia',
    )

    list_filter = ('estado', 'empresa', 'usuario')
    search_fields = ('usuario__username',)
    readonly_fields = ('fecha_apertura',)
