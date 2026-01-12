from django.urls import path
from .views import configurar_impresion, imprimir_etiquetas

app_name = 'impresion'

urlpatterns = [
    path('configurar/', configurar_impresion, name='configurar'),
    path("imprimir-etiquetas/", imprimir_etiquetas, name="imprimir_etiquetas"),
]
