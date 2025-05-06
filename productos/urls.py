from django.urls import path
from . import views



urlpatterns = [
    path('productos/', views.lista_productos, name='lista_productos'),
    path('productos/nuevo/', views.nuevo_producto, name='nuevo_producto'),
    path('productos/editar/<int:id>/', views.editar_producto, name='editar_producto'),
    path('productos/eliminar/<int:id>/', views.eliminar_producto, name='eliminar_producto'),
    path('productos/exportar_pdf/', views.exportar_productos_pdf, name='exportar_productos_pdf'),
    path('productos/nueva_categoria/', views.nueva_categoria, name='nueva_categoria'),
    path('buscar-producto/', views.buscar_producto_por_codigo, name='buscar_producto_por_codigo'),
]
