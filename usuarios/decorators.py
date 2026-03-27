from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def no_empleado_required(view_func):
    """
    Decorator que bloquea acceso a empleados (a menos que sean superuser/staff).
    Solo permite: usuarios normales, superusers y staff.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Permitir si NO es empleado, o si es superuser/staff
        if not request.user.es_empleado or request.user.is_superuser or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # Bloquear empleados normales
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('nueva_venta')
    
    return wrapper