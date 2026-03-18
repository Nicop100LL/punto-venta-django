from django.urls import path
from .views import reporte_diario
from .views import dashboard, reporte_mensual, ranking_productos
from .views import analytics 
from .views import reporte_ganancias 

urlpatterns = [
    path('diario/', reporte_diario, name='reporte_diario'),
    path('dashboard/', dashboard, name='dashboard'),
    path('mensual/', reporte_mensual, name='reporte_mensual'),
    path('ranking/', ranking_productos, name='ranking_productos'),
    path('analytics/', analytics, name='analytics'), 
    path('ganancias/', reporte_ganancias, name='reporte_ganancias'),
]
