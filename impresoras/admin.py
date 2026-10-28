from django import forms
from django.contrib import admin
from .models import ConfiguracionImpresoraTicket


class ConfiguracionImpresoraTicketForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionImpresoraTicket
        fields = "__all__"
        widgets = {
            "saludo_final": forms.Textarea(attrs={
                "rows": 4,
                "cols": 50,
                "wrap": "soft",
                "style": "white-space: pre-wrap; overflow-wrap: break-word;",
            }),
            "datos_empresa": forms.Textarea(attrs={
                "rows": 4,
                "cols": 50,
                "wrap": "soft",
                "style": "white-space: pre-wrap; overflow-wrap: break-word;",
            }),
        }


@admin.register(ConfiguracionImpresoraTicket)
class ConfiguracionImpresoraTicketAdmin(admin.ModelAdmin):
    form = ConfiguracionImpresoraTicketForm  # <-- esta línea es la clave

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