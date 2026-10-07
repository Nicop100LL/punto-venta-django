from django.contrib import admin

from .models import AgenteBalanza, Balanza, CambioBalanza, ProductoBalanza

admin.site.register(AgenteBalanza)
admin.site.register(Balanza)
admin.site.register(ProductoBalanza)


@admin.register(CambioBalanza)
class CambioAdmin(admin.ModelAdmin):
    list_display = ('balanza', 'plu', 'tipo', 'precio', 'estado', 'intentos', 'actualizado')
    list_filter = ('estado', 'tipo', 'balanza')
