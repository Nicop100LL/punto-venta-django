from django.contrib import admin
from .models import  Venta, DetalleVenta

class DetalleInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1

class VentaAdmin(admin.ModelAdmin):
    inlines = [DetalleInline]


admin.site.register(Venta, VentaAdmin)

from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'cuit', 'condicion_iva']  # Ajustá los campos según tu modelo
