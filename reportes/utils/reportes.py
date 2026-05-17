from django.db.models import Sum
from ventas.models import EgresoCaja

def obtener_egresos_periodo(empresa, fecha_inicio, fecha_fin):
    egresos = EgresoCaja.objects.filter(
        empresa=empresa,
        fecha__date__gte=fecha_inicio,
        fecha__date__lte=fecha_fin
    ).select_related('usuario', 'caja').order_by('-fecha')

    total = egresos.aggregate(
        total=Sum('monto')
    )['total'] or 0

    return egresos, total