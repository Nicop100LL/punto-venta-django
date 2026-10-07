from django.urls import path

from . import api, views

app_name = 'balanzas'

urlpatterns = [
    path('', views.panel, name='panel'),
    path('nueva/', views.balanza_nueva, name='balanza_nueva'),
    path('<int:balanza_id>/editar/', views.balanza_editar, name='balanza_editar'),
    path('<int:balanza_id>/productos/', views.productos_balanza, name='productos_balanza'),
    path('<int:balanza_id>/sincronizar/', views.sincronizar_todo, name='sincronizar_todo'),
    path('errores/reintentar/', views.reintentar_errores, name='reintentar_errores'),
    path('etiqueta/agregar/', views.agregar_etiqueta, name='agregar_etiqueta'),
    path('agentes/nuevo/', views.nuevo_agente, name='nuevo_agente'),
    path('api/pendientes/', api.Pendientes.as_view(), name='api_pendientes'),
    path('api/cambios/<int:pk>/confirmar/', api.Confirmar.as_view(), name='api_confirmar'),
    path('api/latido/', api.Latido.as_view(), name='api_latido'),
]
