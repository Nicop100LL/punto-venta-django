from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .utils import get_caja_abierta
from .models import CierreCaja
from decimal import Decimal
from django.utils.timezone import now
from ventas.models import Venta
from django.db.models import Sum



@login_required
def abrir_caja(request):
    usuario = request.user
    empresa = request.user.empresa

    # 🔒 Verificar si ya hay una caja abierta
    caja_abierta = get_caja_abierta(usuario, empresa)

    if caja_abierta:
        messages.warning(request, 'Ya tenés una caja abierta.')
        return redirect(request.META.get('HTTP_REFERER', 'nueva_venta'))

    if request.method == 'POST':
        monto_inicial = Decimal(request.POST.get('monto_inicial') or '0')

        CierreCaja.objects.create(
            usuario=usuario,
            empresa=empresa,
            monto_inicial=monto_inicial
        )

        messages.success(
            request,
            'Caja abierta correctamente.'
        )

        return redirect('nueva_venta')

    return render(request, 'caja/abrir_caja.html')

@login_required
def cerrar_caja(request):
    usuario = request.user
    empresa = request.user.empresa

    caja = get_caja_abierta(usuario, empresa)

    if not caja:
        messages.warning(request, 'No hay una caja abierta.')
        return redirect('nueva_venta')

    # Ventas asociadas a ESTA caja
    ventas = Venta.objects.filter(caja=caja)
    total_ventas = ventas.aggregate(total=Sum('total'))['total'] or Decimal('0')

    total_esperado = caja.monto_inicial + total_ventas

    if request.method == 'POST':
        monto_real = Decimal(request.POST.get('monto_cierre') or '0')

        total_ventas = ventas.aggregate(total=Sum('total'))['total'] or 0
        efectivo_sistema = caja.monto_inicial + total_ventas

        caja.fecha_cierre = now()
        caja.efectivo_sistema = efectivo_sistema
        caja.efectivo_real = monto_real
        caja.saldo_final = monto_real
        caja.diferencia = monto_real - efectivo_sistema
        caja.estado = 'cerrada'

        caja.save()


        messages.success(request, 'Caja cerrada correctamente.')
        return redirect('lista_cajas')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from decimal import Decimal

@login_required
def detalle_caja(request):
    """
    Vista de detalle de caja:
    - Muestra ventas y totales por método de pago
    - Calcula ingreso total, diferencia y saldo final
    """
    caja = get_caja_abierta(request.user, request.user.empresa)

    if not caja:
        return redirect('abrir_caja')

    # Todas las ventas de la caja
    ventas = caja.ventas.all().order_by('numero_empresa')

    # Totales por método de pago
    totales = {
        'EF': sum(v.total for v in ventas if v.tipo_pago == 'EF'),
        'MP': sum(v.total for v in ventas if v.tipo_pago == 'MP'),
        'DN': sum(v.total for v in ventas if v.tipo_pago == 'DN'),
        'TJ': sum(v.total for v in ventas if v.tipo_pago == 'TJ'),
        'TR': sum(v.total for v in ventas if v.tipo_pago == 'TR'),
        'CC': ventas.filter(cuenta_corriente=True).aggregate(t=Sum('total'))['t'] or 0,
    }

    # Totales generales
    total_ventas = sum(v.total for v in ventas)
    total_efectivo = totales['EF']
    total_no_efectivo = total_ventas - total_efectivo
    total_caja = caja.monto_inicial + total_ventas

    # Diferencia y saldo final si la caja está cerrada
    if caja.fecha_cierre:
        saldo_final = getattr(caja, 'saldo_final', total_caja)
        diferencia = saldo_final - total_caja
    else:
        saldo_final = None
        diferencia = None

    context = {
        'caja': caja,
        'ventas': ventas,
        'totales': totales,
        'total_ventas': total_ventas,
        'total_efectivo': total_efectivo,
        'total_no_efectivo': total_no_efectivo,
        'total_caja': total_caja,
        'saldo_final': saldo_final,
        'diferencia': diferencia,
    }

    return render(request, 'caja/detalle_caja.html', context)



@login_required
def lista_cajas(request):
    cajas = CierreCaja.objects.filter(
        empresa=request.user.empresa
    ).order_by('-fecha_apertura')

    return render(request, 'caja/lista_cajas.html', {
        'cajas': cajas
    })


@login_required
def detalle_caja_historica(request, caja_id):
    caja = get_object_or_404(
        CierreCaja,
        id=caja_id,
        empresa=request.user.empresa
    )

    ventas = Venta.objects.filter(caja=caja)

    total_ventas = ventas.aggregate(
        total=Sum('total')
    )['total'] or 0

    totales_por_pago = ventas.values('tipo_pago').annotate(
        total=Sum('total')
    )

    # Inicializamos en 0
    totales = {
        'EF': 0,
        'MP': 0,
        'DN': 0,
        'TJ': 0,
        'TR': 0,
        'CC': 0,  # cuenta corriente (opcional)
    }

    for t in totales_por_pago:
        totales[t['tipo_pago']] = t['total'] or 0

    return render(request, 'caja/detalle_caja_historica.html', {
        'caja': caja,
        'ventas': ventas,
        'total_ventas': total_ventas,
        'totales': totales,
    })
