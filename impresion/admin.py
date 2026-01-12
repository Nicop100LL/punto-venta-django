from django.contrib import admin
from .models import ModeloImpresion

@admin.register(ModeloImpresion)
class ModeloImpresionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "tamano_hoja", "orientacion", "activo")
    list_filter = ("empresa", "activo")
    search_fields = ("nombre",)
