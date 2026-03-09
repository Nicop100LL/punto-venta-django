from django.contrib import admin
from .models import Venta, DetalleVenta, ReglaArcaPago, Cliente

# Inline para detalle de venta
class DetalleInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1

# Admin para venta
class VentaAdmin(admin.ModelAdmin):
    inlines = [DetalleInline]

admin.site.register(Venta, VentaAdmin)

# Admin para reglas de ARCA
@admin.register(ReglaArcaPago)
class ReglaArcaPagoAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'tipo_pago', 'subir_a_arca', 'tipo_comprobante')
    list_filter = ('empresa', 'tipo_pago', 'subir_a_arca')