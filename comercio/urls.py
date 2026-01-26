from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from django.contrib.auth import views as auth_views
from usuarios.views import login_view
from ventas import views
from reportes.views import dashboard
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('productos/', include('productos.urls')),
    path('registration/login/', login_view, name='login'),
    path('ventas/editar_cliente/', views.editar_cliente, name='editar_cliente'),
    path('', views.nueva_venta, name='nueva_venta'),
    path('ventas/', include('ventas.urls')),
    path('reportes/', include('reportes.urls')),
    path('dashboard/', dashboard, name='dashboard'),
    path('impresion/', include('impresion.urls')),
    path('caja/', include('caja.urls')),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)