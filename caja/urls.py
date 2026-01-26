
from django.urls import path
from . import views

urlpatterns = [
    path('abrir/', views.abrir_caja, name='abrir_caja'),
    path('detalle/', views.detalle_caja, name='detalle_caja'),  # caja actual
    path('lista/', views.lista_cajas, name='lista_cajas'),
    path('<int:caja_id>/', views.detalle_caja_historica, name='detalle_caja_historica'),
    path('cerrar/', views.cerrar_caja, name='cerrar_caja'),
]
