from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_presupuestos, name='lista_presupuestos'),
    path('nuevo/', views.nuevo_presupuesto, name='nuevo_presupuesto'),
    path('detalle/<int:presupuesto_id>/', views.detalle_presupuesto, name='detalle_presupuesto'),
    path('anular/<int:presupuesto_id>/', views.anular_presupuesto, name='anular_presupuesto'),
    path('cancelar/', views.cancelar_borrador, name='cancelar_presupuesto'),
]