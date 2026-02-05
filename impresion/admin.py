from django.contrib import admin
from .models import ModeloImpresion, ModeloEtiqueta

@admin.register(ModeloImpresion)
class ModeloImpresionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "tamano_hoja", "orientacion", "activo")
    list_filter = ("empresa", "activo")
    search_fields = ("nombre",)

@admin.register(ModeloEtiqueta)
class ModeloEtiquetaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "ancho_mm", "alto_mm", "activo")
    list_filter = ("empresa", "activo")
    search_fields = ("nombre",)
