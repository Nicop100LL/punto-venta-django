from django.contrib import admin
from .models import Venta, DetalleVenta, Cliente

# Inline para detalle de venta
class DetalleInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1

# Admin para venta
class VentaAdmin(admin.ModelAdmin):
    inlines = [DetalleInline]

admin.site.register(Venta, VentaAdmin)
