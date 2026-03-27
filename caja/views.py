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
from ventas.models import NotaCredito
from usuarios.decorators import no_empleado_required


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

    ventas = Venta.objects.filter(caja=caja)

    # Separar totales por tipo
    total_ventas = ventas.aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    # Solo efectivo para el control físico
    total_efectivo_ventas = ventas.filter(
        tipo_pago='EF', cuenta_corriente=False
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')

    # Notas de crédito — solo las de efectivo afectan la caja física
    notas_credito = NotaCredito.objects.filter(caja=caja, estado='aplicada')
    nc_efectivo = notas_credito.filter(
        venta__tipo_pago='EF'
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')

    # Lo que debería haber en caja (solo efectivo)
    efectivo_sistema = caja.monto_inicial + total_efectivo_ventas - nc_efectivo

    if request.method == 'POST':
        monto_real = Decimal(request.POST.get('monto_cierre') or '0')

        caja.fecha_cierre = now()
        caja.efectivo_sistema = efectivo_sistema   # solo EF
        caja.efectivo_real = monto_real
        caja.saldo_final = monto_real
        caja.diferencia = monto_real - efectivo_sistema  # diferencia real
        caja.estado = 'cerrada'
        caja.save()

        messages.success(request, 'Caja cerrada correctamente.')
        return redirect('lista_cajas')

    # Totales informativos para mostrar en el formulario
    totales_digitales = {
        'MP': ventas.filter(tipo_pago='MP').aggregate(t=Sum('total'))['t'] or Decimal('0'),
        'DN': ventas.filter(tipo_pago='DN').aggregate(t=Sum('total'))['t'] or Decimal('0'),
        'TJ': ventas.filter(tipo_pago='TJ').aggregate(t=Sum('total'))['t'] or Decimal('0'),
        'TR': ventas.filter(tipo_pago='TR').aggregate(t=Sum('total'))['t'] or Decimal('0'),
    }

    context = {
        'caja': caja,
        'efectivo_sistema': efectivo_sistema,
        'total_ventas': total_ventas,
        'totales_digitales': totales_digitales,
        'total_efectivo_ventas': total_efectivo_ventas,
    }

    return render(request, 'caja/cerrar_caja.html', context)


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from decimal import Decimal


@login_required
def detalle_caja(request):
    """
    Vista de detalle de caja:
    - Muestra ventas y totales por método de pago
    - Calcula ingreso total, diferencia y saldo final
    - Incluye las Notas de Crédito aplicadas
    """
    caja = get_caja_abierta(request.user, request.user.empresa)
    if not caja:
        return redirect('abrir_caja')

    # Todas las ventas de la caja
    ventas = caja.ventas.all().order_by('numero_empresa')
    ventas_ids = ventas.values_list('id', flat=True)

    # Notas de crédito aplicadas de esas ventas
    notas_credito = NotaCredito.objects.filter(
        venta_id__in=ventas_ids,
        estado='aplicada'
    )
    total_notas_credito = notas_credito.aggregate(total=Sum('total'))['total'] or Decimal('0')

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

    # Total efectivo real en caja, descontando notas de crédito
    total_caja = caja.monto_inicial + total_ventas - total_notas_credito

    # Diferencia y saldo final
    if caja.fecha_cierre:
        saldo_final = caja.saldo_final if caja.saldo_final is not None else total_caja
        diferencia = saldo_final - total_caja
    else:
        saldo_final = total_caja
        diferencia = Decimal('0.00')

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
        'notas_credito': notas_credito,
        'total_notas_credito': total_notas_credito,
    }

    return render(request, 'caja/detalle_caja.html', context)



@login_required
@no_empleado_required
def lista_cajas(request):
    cajas = CierreCaja.objects.filter(
        empresa=request.user.empresa
    ).order_by('-fecha_apertura')

    return render(request, 'caja/lista_cajas.html', {
        'cajas': cajas
    })


@login_required
@no_empleado_required
def detalle_caja_historica(request, caja_id):
    caja = get_object_or_404(
        CierreCaja,
        id=caja_id,
        empresa=request.user.empresa
    )

    ventas = Venta.objects.filter(caja=caja).order_by('numero_empresa')
    ventas_ids = ventas.values_list('id', flat=True)
    total_ventas = ventas.aggregate(total=Sum('total'))['total'] or Decimal('0')

    # Totales por método (informativos, sin CC duplicado)
    totales = {'EF': Decimal('0'), 'MP': Decimal('0'), 'DN': Decimal('0'),
               'TJ': Decimal('0'), 'TR': Decimal('0'), 'CC': Decimal('0')}

    for v in ventas:
        if v.cuenta_corriente:
            totales['CC'] += v.total
        else:
            totales[v.tipo_pago] += v.total

    # Notas de crédito
    notas_credito = NotaCredito.objects.filter(
        venta_id__in=ventas_ids,
        caja=caja,
        estado='aplicada'
    ).select_related('venta')

    total_notas_credito = notas_credito.aggregate(total=Sum('total'))['total'] or Decimal('0')

    # Descontar NC de cada método
    for nc in notas_credito:
        if nc.venta.cuenta_corriente:
            totales['CC'] -= nc.total
        else:
            totales[nc.venta.tipo_pago] -= nc.total

    # ✅ Efectivo físico esperado:
    #    Solo ventas EF no-CC, menos NC de ventas EF no-CC
    ventas_ef = sum(v.total for v in ventas
                    if v.tipo_pago == 'EF' and not v.cuenta_corriente)

    nc_ef = sum(nc.total for nc in notas_credito
                if nc.venta.tipo_pago == 'EF' and not nc.venta.cuenta_corriente)

    efectivo_esperado = caja.monto_inicial + ventas_ef - nc_ef

    # Para el historial usamos efectivo_sistema guardado al cierre
    # Si no existe (cajas viejas), calculamos como fallback
    if caja.fecha_cierre:
        saldo_final = caja.efectivo_real if caja.efectivo_real is not None else efectivo_esperado
        # efectivo_sistema guardado > calculado (para cajas nuevas)
        base_diferencia = caja.efectivo_sistema if caja.efectivo_sistema else efectivo_esperado
        diferencia = saldo_final - base_diferencia
    else:
        saldo_final = efectivo_esperado
        diferencia = Decimal('0')

    context = {
        'caja': caja,
        'ventas': ventas,
        'totales': totales,
        'total_ventas': total_ventas,
        'notas_credito': notas_credito,
        'total_notas_credito': total_notas_credito,
        # Renombramos para claridad en el template
        'efectivo_esperado': efectivo_esperado,
        'saldo_final': saldo_final,
        'diferencia': diferencia,
        # Informativos para mostrar en tarjetas
        'ventas_ef': ventas_ef,
        'nc_ef': nc_ef,
    }

    return render(request, 'caja/detalle_caja_historica.html', context)