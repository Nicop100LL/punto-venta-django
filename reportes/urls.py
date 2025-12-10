from django.urls import path
from .views import reporte_diario
from .views import dashboard, reporte_mensual, ranking_productos

urlpatterns = [
    path('diario/', reporte_diario, name='reporte_diario'),
    path('dashboard/', dashboard, name='dashboard'),
    path('mensual/', reporte_mensual, name='reporte_mensual'),
    path('ranking/', ranking_productos, name='ranking_productos'),
]
