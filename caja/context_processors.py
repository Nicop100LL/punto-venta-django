from django.db.models import Sum
from ventas.models import Venta
from .utils import get_caja_abierta

def caja_actual(request):
    if not request.user.is_authenticated:
        return {}

    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return {}

    caja = get_caja_abierta(request.user, empresa)

    if not caja:
        return {
            'caja_abierta': None
        }

    ventas = Venta.objects.filter(caja=caja)

    total_ventas = ventas.aggregate(total=Sum('total'))['total'] or 0
    total_efectivo = ventas.filter(tipo_pago='EF').aggregate(total=Sum('total'))['total'] or 0
    total_no_efectivo = total_ventas - total_efectivo
    total_caja = caja.monto_inicial + total_ventas

    return {
        'caja_abierta': caja,
        'total_ventas': total_ventas,
        'total_efectivo': total_efectivo,
        'total_no_efectivo': total_no_efectivo,
        'total_caja': total_caja,
    }
