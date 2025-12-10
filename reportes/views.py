# reportes/views.py
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, F
from django.contrib.auth.decorators import login_required
import datetime
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from ventas.models import Venta, DetalleVenta
import math
from django.db.models import Sum, F
from decimal import Decimal

from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.contrib.auth.decorators import login_required
import datetime

from ventas.models import Venta, DetalleVenta

def convertir_a_bultos(cantidad):
    if cantidad <= 0:
        return 0
    if cantidad < 1:
        return 1
    return math.floor(cantidad)

@login_required
def reporte_diario(request):
    empresa = request.user.empresa

    # -----------------------------
    # 1) Fecha (GET ?fecha=YYYY-MM-DD) o hoy
    # -----------------------------
    fecha_str = request.GET.get('fecha')
    if fecha_str:
        try:
            fecha = datetime.date.fromisoformat(fecha_str)
        except Exception:
            fecha = timezone.localdate()
    else:
        fecha = timezone.localdate()

    # -----------------------------
    # 2) Ventas del día
    # -----------------------------
    ventas_qs = Venta.objects.filter(empresa=empresa, fecha__date=fecha)
    

    # -----------------------------
    # 3) Obtener todos los productos para el <select>
    # -----------------------------
    productos = DetalleVenta.objects.filter(
        venta__empresa=empresa
    ).values('producto__id', 'producto__nombre').distinct()

    # -----------------------------
    # 4) Filtrado por producto (GET ?producto=ID)
    # -----------------------------
    producto_id = request.GET.get('producto')
    detalles_qs = DetalleVenta.objects.filter(venta__in=ventas_qs)
    if producto_id:
        detalles_qs = detalles_qs.filter(producto_id=producto_id)

    # -----------------------------
    # 5) Totales generales
    # -----------------------------
    total_ventas = ventas_qs.aggregate(total=Sum('total'))['total'] or 0
    cantidad_ventas = ventas_qs.count()

    total_productos = detalles_qs.aggregate(total_cant=Sum('cantidad'))['total_cant'] or 0
    cantidad_tickets = ventas_qs.count()
    ticket_promedio = total_ventas / cantidad_tickets if cantidad_tickets > 0 else 0

    # -----------------------------
    # 6) Agregación por producto
    # -----------------------------
    detalles_con_subtotal = detalles_qs.annotate(
        subtotal=ExpressionWrapper(
            F('cantidad') * F('precio_unitario'),
            output_field=DecimalField()
        )
    )

    ventas = detalles_con_subtotal.values(
        'producto__id', 'producto__nombre'
    ).annotate(
        cantidad=Sum('cantidad'),
        total=Sum('subtotal')
    )
    
    # --------------------------------
    # Transformar cantidades en BULTOS
    # --------------------------------
    ventas = list(ventas)  # materializar antes de modificar

        
    for v in ventas:
        try:
            cantidad_val = float(v.get('cantidad', 0) or 0)
        except (TypeError, ValueError):
            cantidad_val = 0.0

        # Aplicar regla de bultos
        if cantidad_val <= 0:
            v['cantidad'] = 0
        elif cantidad_val < 1:
            v['cantidad'] = 1
        else:
            v['cantidad'] = math.floor(cantidad_val)

        # porcentaje sobre el total
        total_val = float(v.get('total', 0) or 0)
        v['porcentaje'] = (total_val / float(total_ventas or 1) * 100) if total_ventas > 0 else 0
        
    # Calcular total de bultos
    total_bultos = sum(v['cantidad'] for v in ventas)


    # Ordenamiento
    orden = request.GET.get("orden")
    if orden == "cantidad":
        ventas = sorted(ventas, key=lambda x: x['cantidad'], reverse=True)
    elif orden == "total":
        ventas = sorted(ventas, key=lambda x: x['total'], reverse=True)
    else:
        ventas = sorted(ventas, key=lambda x: x['producto__nombre'])

    # -----------------------------
    # 7) Totales por tipo de pago
    # -----------------------------
    totales_pago_qs = ventas_qs.values('tipo_pago').annotate(total=Sum('total'))
    TIPOS = dict(Venta.TIPO_PAGO_CHOICES)
    totales_pago = [
        {'tipo_pago': TIPOS.get(p['tipo_pago'], p['tipo_pago']), 'total': p['total'] or 0}
        for p in totales_pago_qs
    ]

    # -----------------------------
    # 8) Contexto para template
    # -----------------------------
    context = {
        'fecha': fecha.isoformat(),
        'ventas': ventas,
        'productos': productos,  # para el <select> de filtrado
        'total_ventas': total_ventas,
        'cantidad_ventas': cantidad_ventas,
        'totales_pago': totales_pago,
        'cantidad_tickets': cantidad_tickets,
        'ticket_promedio': ticket_promedio,
        'producto_filtrado': producto_id,  # para marcar la opción seleccionada
        'total_productos': total_bultos, 
    }

    return render(request, 'reportes/reporte_diario.html', context)


@login_required
def dashboard(request):
    empresa = request.user.empresa

    hoy = timezone.localdate()

    # Ventas de hoy
    ventas_qs = Venta.objects.filter(empresa=empresa, fecha__date=hoy)

    total_ventas = ventas_qs.aggregate(total=Sum('total'))['total'] or 0
    cantidad_tickets = ventas_qs.count()
    ticket_promedio = total_ventas / cantidad_tickets if cantidad_tickets > 0 else 0

    # Productos vendidos
    detalles_qs = DetalleVenta.objects.filter(venta__in=ventas_qs)

    ventas = (
        detalles_qs
        .values('producto__nombre')
        .annotate(cantidad=Sum('cantidad'))
        .order_by('-cantidad')[:5]
    )

    # Tipos de pago
    totales_pago = ventas_qs.values('tipo_pago').annotate(total=Sum('total'))

    context = {
        'hoy': hoy,
        'total_ventas': total_ventas,
        'ticket_promedio': ticket_promedio,
        'cantidad_tickets': cantidad_tickets,
        'top5': ventas,
        'totales_pago': totales_pago,
    }

    return render(request, 'reportes/dashboard.html', context)


@login_required
def reporte_mensual(request):
    return render(request, 'reportes/reporte_mensual.html')

@login_required
def ranking_productos(request):
    return render(request, 'reportes/ranking_productos.html')
