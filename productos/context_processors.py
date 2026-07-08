from datetime import timedelta
from django.utils import timezone
from .models import Producto, ControlAvisoVencimiento

HORAS_ENTRE_AVISOS = 8  # cada cuántas horas se repite el aviso (8 = ~3 veces por día)


def productos_por_vencer_context(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'empresa'):
        return {}

    empresa = request.user.empresa
    ahora = timezone.now()
    hoy = ahora.date()

    control, _ = ControlAvisoVencimiento.objects.get_or_create(empresa=empresa)

    if control.ultimo_aviso and (ahora - control.ultimo_aviso) < timedelta(hours=HORAS_ENTRE_AVISOS):
        return {'productos_por_vencer': []}

    productos = Producto.objects.filter(
        empresa=empresa,
        fecha_vencimiento__isnull=False
    )
    productos_por_vencer = [
        {
            'nombre': p.nombre,
            'fecha_vencimiento': p.fecha_vencimiento.isoformat(),
            'fecha_vencimiento_legible': p.fecha_vencimiento.strftime('%d/%m/%Y'),
        }
        for p in productos
        if (p.fecha_vencimiento - hoy).days <= (p.dias_aviso_vencimiento or 7)
    ]

    if productos_por_vencer:
        control.ultimo_aviso = ahora
        control.save()

    return {'productos_por_vencer': productos_por_vencer}