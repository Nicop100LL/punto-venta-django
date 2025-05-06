from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_ventas, name='lista_ventas'),
    path('nueva/', views.nueva_venta, name='nueva_venta'),
    path('detalle/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),
    path('venta/<int:venta_id>/pdf/', views.venta_pdf, name='venta_pdf'),
    path('lista_clientes/', views.lista_clientes, name='lista_clientes'),
    path('nuevo_cliente/', views.nuevo_cliente, name='nuevo_cliente'),
    path('editar_cliente/<int:cliente_id>/', views.editar_cliente, name='editar_cliente'),
    path('ajax/obtener_saldo/', views.obtener_saldo_cliente, name='obtener_saldo_cliente'),
    path('modificar-saldo-cliente/', views.modificar_saldo_cliente, name='modificar_saldo_cliente'),
]
