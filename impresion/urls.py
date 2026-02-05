from django.urls import path
from .views import configurar_impresion, imprimir_etiquetas, imprimir_etiquetas_pdf

app_name = 'impresion'

urlpatterns = [
    path('configurar/', configurar_impresion, name='configurar'),
    path("imprimir-etiquetas/", imprimir_etiquetas, name="imprimir_etiquetas"),
    path(
        "etiquetas/",
        imprimir_etiquetas,
        name="imprimir_etiquetas"
    ),
    path(
        "etiquetas/pdf/",
        imprimir_etiquetas_pdf,
        name="imprimir_etiquetas_pdf"
    ),
]
