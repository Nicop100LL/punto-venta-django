import time
from decimal import ROUND_HALF_UP, Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from productos.models import Producto

from .forms import BalanzaForm
from .models import AgenteBalanza, Balanza, CambioBalanza, ProductoBalanza
from .services import buscar_por_etiqueta, registrar_cambio


def balanza_habilitada(vista):
    @wraps(vista)
    def _v(request, *a, **k):
        empresa = getattr(request.user, 'empresa', None)
        if not empresa or not empresa.usa_balanza:
            raise Http404
        return vista(request, *a, **k)
    return login_required(_v)


def _contexto_panel(request):
    e = request.user.empresa
    balanzas = (Balanza.objects.filter(empresa=e).select_related('agente').annotate(
        pendientes=Count('cambios', filter=Q(cambios__estado='pendiente')),
        errores=Count('cambios', filter=Q(cambios__estado='error'))))
    return {
        'balanzas': balanzas,
        'agentes': AgenteBalanza.objects.filter(empresa=e),
        'errores': CambioBalanza.objects.filter(balanza__empresa=e, estado='error')
                   .select_related('balanza').order_by('-actualizado')[:20],
        'recientes': CambioBalanza.objects.filter(balanza__empresa=e)
                     .select_related('balanza').order_by('-actualizado')[:15],
    }


@balanza_habilitada
def panel(request):
    return render(request, 'balanzas/panel.html', _contexto_panel(request))


@balanza_habilitada
@require_POST
def nuevo_agente(request):
    nombre = (request.POST.get('nombre') or 'Agente local').strip()[:100]
    agente, token = AgenteBalanza.crear_con_token(request.user.empresa, nombre)
    ctx = _contexto_panel(request)
    ctx.update(token_nuevo=token, agente_nuevo=agente)
    return render(request, 'balanzas/panel.html', ctx)


@balanza_habilitada
def balanza_nueva(request):
    form = BalanzaForm(request.POST or None, empresa=request.user.empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Balanza creada. Ahora elegí qué productos enviar.')
        return redirect('balanzas:panel')
    return render(request, 'balanzas/balanza_form.html', {'form': form, 'titulo': 'Nueva balanza'})


@balanza_habilitada
def balanza_editar(request, balanza_id):
    b = get_object_or_404(Balanza, id=balanza_id, empresa=request.user.empresa)
    form = BalanzaForm(request.POST or None, instance=b, empresa=request.user.empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Balanza actualizada.')
        return redirect('balanzas:panel')
    return render(request, 'balanzas/balanza_form.html',
                  {'form': form, 'titulo': f'Editar {b.nombre}'})


@balanza_habilitada
def productos_balanza(request, balanza_id):
    empresa = request.user.empresa
    balanza = get_object_or_404(Balanza, id=balanza_id, empresa=empresa)
    productos = list(Producto.objects.filter(empresa=empresa, activo=True, venta_por_caja=False)
                     .select_related('categoria').order_by('categoria__nombre', 'nombre'))
    asignados = {pb.producto_id: pb for pb in balanza.productos.select_related('producto')}
    if request.method == 'POST':
        return _guardar_productos(request, balanza, productos, asignados)
    filas = [{'p': p, 'pb': asignados.get(p.id)} for p in productos]
    return render(request, 'balanzas/productos_balanza.html', {'balanza': balanza, 'filas': filas})


def _guardar_productos(request, balanza, productos, asignados):
    volver = redirect('balanzas:productos_balanza', balanza_id=balanza.id)
    por_id = {p.id: p for p in productos}
    seleccion = {}  # producto_id -> PLU (None = asignar automático)
    for p in productos:
        if not request.POST.get(f'incluir_{p.id}'):
            continue
        raw = (request.POST.get(f'plu_{p.id}') or '').strip()
        if raw:
            if not raw.isdigit() or not 1 <= int(raw) <= 999999:
                messages.error(request, f'PLU inválido para "{p.nombre}": {raw}')
                return volver
            seleccion[p.id] = int(raw)
        else:
            seleccion[p.id] = asignados[p.id].plu if p.id in asignados else None

    n_p = balanza.formato_etiqueta.count('P')
    limite = min(999999, 10 ** n_p - 1) if n_p else 999999
    pasados = [v for v in seleccion.values() if v is not None and v > limite]
    if pasados:
        messages.error(request, f'El formato de etiqueta ({balanza.formato_etiqueta}) solo admite '
                                f'PLU hasta {limite}. Revisá: {pasados[0]}.')
        return volver
    fijos = [v for v in seleccion.values() if v is not None]
    ocultos = {pb.plu for pid, pb in asignados.items() if pid not in por_id}
    if len(fijos) != len(set(fijos)) or set(fijos) & ocultos:
        messages.error(request, 'Hay números de PLU repetidos.')
        return volver
    ocupados = set(fijos) | ocultos
    siguiente = 1
    for pid, plu in seleccion.items():
        if plu is None:
            while siguiente in ocupados:
                siguiente += 1
            if siguiente > limite:
                messages.error(request, 'No quedan PLU libres.')
                return volver
            seleccion[pid] = siguiente
            ocupados.add(siguiente)

    try:
        with transaction.atomic():
            for pid, pb in asignados.items():            # quitados -> baja
                if pid in por_id and pid not in seleccion:
                    registrar_cambio(pb, 'baja', producto=pb.producto)
                    pb.delete()
            for pid, plu in seleccion.items():           # nuevos / PLU cambiado
                p, pb = por_id[pid], asignados.get(pid)
                if pb is None:
                    pb = ProductoBalanza.objects.create(balanza=balanza, producto=p, plu=plu)
                    registrar_cambio(pb, 'alta', producto=p)
                elif pb.plu != plu:
                    registrar_cambio(pb, 'baja', producto=p)
                    pb.plu = plu
                    pb.save(update_fields=['plu'])
                    registrar_cambio(pb, 'alta', producto=p)
    except IntegrityError:
        messages.error(request, 'Conflicto de PLU al guardar. Revisá los números.')
        return volver
    messages.success(request, f'Guardado: {len(seleccion)} producto(s) en la balanza.')
    return redirect('balanzas:panel')


@balanza_habilitada
@require_POST
def sincronizar_todo(request, balanza_id):
    b = get_object_or_404(Balanza, id=balanza_id, empresa=request.user.empresa)
    n = 0
    for pb in b.productos.select_related('producto'):
        if pb.producto.activo and not pb.producto.venta_por_caja:
            registrar_cambio(pb, 'alta')
            n += 1
    messages.success(request, f'{n} producto(s) encolados para enviar a "{b.nombre}".')
    return redirect('balanzas:panel')


@balanza_habilitada
@require_POST
def reintentar_errores(request):
    n = CambioBalanza.objects.filter(balanza__empresa=request.user.empresa,
                                     estado='error').update(estado='pendiente', intentos=0,
                                                            error_detalle='')
    messages.success(request, f'{n} cambio(s) vuelven a la cola.')
    return redirect('balanzas:panel')


@balanza_habilitada
@require_POST
def agregar_etiqueta(request):
    """Lee el código de barras de una etiqueta de balanza y agrega la línea al carrito
    (sesión) con el importe ya calculado. Si el código no es una etiqueta, avisa para
    que la pantalla de ventas siga con el flujo normal."""
    codigo = (request.POST.get('codigo') or '').strip()
    res = buscar_por_etiqueta(request.user.empresa, codigo)
    if res is None:
        return JsonResponse({'success': False, 'no_etiqueta': True})
    producto, importe = res
    precio = producto.precio_venta
    if precio <= 0:
        return JsonResponse({'success': False,
                             'message': f'"{producto.nombre}" tiene precio 0 en el sistema.'})
    cociente = importe / precio
    if producto.tipo_venta == 'unidad':
        cantidad = max(Decimal(1), cociente.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    else:
        cantidad = max(Decimal('0.001'), cociente.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))

    carrito = request.session.get('carrito', [])
    carrito.append({
        'producto_id': producto.id,
        'nombre': producto.nombre,
        'precio_unitario': float(precio),
        'cantidad': float(cantidad),
        'subtotal': float(importe),           # el importe de la etiqueta manda
        'descuento': 0.0,
        'tipo_precio': None,
        'ahorro_unitario': 0,
        'venta_por_caja': False,
        'codigo_unico': f'_bal{int(time.time() * 1000)}',   # línea propia, "Quitar" funciona
        'detalle': 'Pesado en balanza',
    })
    request.session['carrito'] = carrito
    request.session.modified = True
    return JsonResponse({'success': True, 'nombre': producto.nombre,
                         'cantidad': float(cantidad), 'importe': float(importe)})
