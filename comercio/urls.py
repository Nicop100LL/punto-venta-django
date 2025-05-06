from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from django.contrib.auth import views as auth_views
from usuarios.views import login_view


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('productos/', include('productos.urls')),
    path('registration/login/', login_view, name='login'),

    path('', lambda request: HttpResponse("Bienvenido, estás logueado!"), name='home'),
    path('ventas/', include('ventas.urls')),

]
