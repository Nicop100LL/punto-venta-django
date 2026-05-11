from django.urls import path
from . import views



urlpatterns = [
    path('productos/', views.lista_productos, name='lista_productos'),
    path('productos/nuevo/', views.nuevo_producto, name='nuevo_producto'),
    path('productos/editar/<int:id>/', views.editar_producto, name='editar_producto'),
    path('productos/eliminar/<int:id>/', views.eliminar_producto, name='eliminar_producto'),
    path('productos/exportar_pdf/', views.exportar_productos_pdf, name='exportar_productos_pdf'),
    path('exportar-excel/', views.exportar_productos_excel, name='exportar_productos_excel'),
    path('productos/nueva_categoria/', views.nueva_categoria, name='nueva_categoria'),
    path('buscar-producto/', views.buscar_producto_por_codigo, name='buscar_producto_por_codigo'),
     path(
        "generar-codigo/",
        views.generar_codigo_producto,
        name="generar_codigo_producto"
    ),
     path('producto/actualizar-inline/', views.actualizar_producto_inline, name='actualizar_producto_inline'),
     path('edicion-masiva/', views.lista_productos_edicion_masiva, name='lista_productos_edicion_masiva'),
     path('edicion-masiva/actualizar-precios/', views.actualizar_precios_masivo, name='actualizar_precios_masivo'),
     path('crear-categoria/', views.crear_categoria, name='crear_categoria'),
]
