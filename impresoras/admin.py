from django.contrib import admin
from .models import ConfiguracionImpresoraTicket


@admin.register(ConfiguracionImpresoraTicket)
class ConfiguracionImpresoraTicketAdmin(admin.ModelAdmin):
    list_display = (
        "empresa",
        "nombre_sistema",
        "ancho_mm",
        "cortar_papel",
        "abrir_cajon",
        "activo",
        "agente_puerto",
    )
    list_filter = ("activo", "ancho_mm")
    search_fields = ("empresa__nombre", "nombre_sistema")
    readonly_fields = ("agente_token",)
