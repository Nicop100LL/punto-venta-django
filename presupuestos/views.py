from decimal import Decimal, InvalidOperation, ROUND_CEILING
from functools import wraps
from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from productos.models import Producto
from ventas.models import Cliente
from .models import Presupuesto, DetallePresupuesto
from .services import armar_item

SESSION_KEYS = ('presupuesto_carrito', 'presupuesto_cliente_id',
                'presupuesto_cliente_nombre', 'presupuesto_nota', 'presupuesto_validez')


def presupuestos_habilitados(view_func):
    """Login + solo empresas con venta por caja activada."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.empresa.usa_venta_por_caja:
            raise Http404("Presupuestos no habilitados para esta empresa")
        return view_func(request, *args, **kwargs)
    return login_required(_wrapped)


@presupuestos_habilitados
def nuevo_presupuesto(request):
    empresa = request.user.empresa
    session = request.session
    carrito = session.get('presupuesto_carrito', [])

    if request.method == 'POST':
        # Guardar cabecera en sesión (para que persista al agregar/quitar)
        session['presupuesto_cliente_id'] = request.POST.get('cliente') or None
        session['presupuesto_cliente_nombre'] = request.POST.get('cliente_nombre', '').strip()
        session['presupuesto_nota'] = request.POST.get('nota', '')
        session['presupuesto_validez'] = request.POST.get('validez_dias') or '7'

        # ---------- AGREGAR ----------
        if 'agregar' in request.POST:
            codigo = request.POST.get('codigo', '').strip()
            try:
                cantidad = Decimal(request.POST.get('cantidad') or '1')
            except InvalidOperation:
                cantidad = Decimal('1')

            producto = Producto.objects.filter(
                codigo=codigo, empresa=empresa, activo=True
            ).first()

            if not producto:
                messages.error(request, f'Producto no encontrado o inactivo. Código: {codigo}')
            else:
                # Si ingresó m² necesarios, convertir a cajas (redondeo hacia arriba)
                m2 = request.POST.get('m2_necesarios')
                if m2 and producto.venta_por_caja and producto.metros_cuadrados_por_caja:
                    try:
                        cantidad = (Decimal(m2) / producto.metros_cuadrados_por_caja
                                    ).to_integral_value(rounding=ROUND_CEILING)
                    except InvalidOperation:
                        pass

                idx = next((i for i, it in enumerate(carrito)
                            if it['producto_id'] == producto.id), None)
                if idx is not None:
                    cantidad += Decimal(str(carrito[idx]['cantidad']))
                    carrito[idx] = armar_item(empresa, producto, cantidad)
                else:
                    carrito.append(armar_item(empresa, producto, cantidad))

            session['presupuesto_carrito'] = carrito
            session.modified = True
            return redirect('nuevo_presupuesto')

        # ---------- QUITAR ----------
        if 'eliminar' in request.POST:
            try:
                carrito.pop(int(request.POST['eliminar']))
            except (ValueError, IndexError):
                pass
            session['presupuesto_carrito'] = carrito
            session.modified = True
            return redirect('nuevo_presupuesto')

        # ---------- GUARDAR ----------
        if 'guardar' in request.POST:
            if not carrito:
                messages.error(request, 'El presupuesto está vacío.')
                return redirect('nuevo_presupuesto')

            with transaction.atomic():
                ultimo = Presupuesto.objects.filter(empresa=empresa).aggregate(
                    m=Max('numero_empresa'))['m'] or 0

                cliente = None
                if session.get('presupuesto_cliente_id'):
                    cliente = Cliente.objects.filter(
                        id=session['presupuesto_cliente_id'], empresa=empresa
                    ).first()

                try:
                    validez = int(session.get('presupuesto_validez') or 7)
                except ValueError:
                    validez = 7

                p = Presupuesto.objects.create(
                    empresa=empresa,
                    usuario=request.user,
                    cliente=cliente,
                    cliente_nombre=session.get('presupuesto_cliente_nombre', ''),
                    numero_empresa=ultimo + 1,
                    validez_dias=validez,
                    nota=session.get('presupuesto_nota', ''),
                    total=sum(Decimal(str(i['subtotal'])) for i in carrito),
                )
                for it in carrito:
                    DetallePresupuesto.objects.create(
                        presupuesto=p,
                        producto_id=it['producto_id'],
                        descripcion=it['nombre'],
                        cantidad=it['cantidad'],
                        precio_unitario=it['precio_unitario'],
                        metros_por_caja=it.get('metros_por_caja'),
                        metros_totales=it.get('metros_totales'),
                        precio_m2=it.get('precio_m2'),
                    )

            for k in SESSION_KEYS:
                session.pop(k, None)
            return redirect('detalle_presupuesto', presupuesto_id=p.id)

    return render(request, 'presupuestos/nuevo_presupuesto.html', {
        'carrito': carrito,
        'total': sum(float(i['subtotal']) for i in carrito),
        'clientes': Cliente.objects.filter(empresa=empresa),
        'cliente_id': session.get('presupuesto_cliente_id'),
        'cliente_nombre': session.get('presupuesto_cliente_nombre', ''),
        'nota': session.get('presupuesto_nota', ''),
        'validez_dias': session.get('presupuesto_validez', '7'),
    })


@presupuestos_habilitados
def lista_presupuestos(request):
    ver_todos = request.GET.get('ver') == 'todos'
    qs = (Presupuesto.objects
          .filter(empresa=request.user.empresa)
          .select_related('cliente', 'usuario'))
    if not ver_todos:
        qs = qs.filter(fecha__gte=timezone.now() - timedelta(days=30))
    return render(request, 'presupuestos/lista_presupuestos.html', {
        'presupuestos': qs[:200],
        'ver_todos': ver_todos,
    })
    
@presupuestos_habilitados
def detalle_presupuesto(request, presupuesto_id):
    p = get_object_or_404(Presupuesto, id=presupuesto_id, empresa=request.user.empresa)
    detalles = p.detalles.all()
    total_cajas = sum(d.cantidad for d in detalles if d.metros_por_caja)
    total_metros = sum(d.metros_totales or 0 for d in detalles)
    return render(request, 'presupuestos/detalle_presupuesto_a4.html', {
        'presupuesto': p,
        'empresa': request.user.empresa,
        'total_cajas': total_cajas,
        'total_metros': total_metros,
    })


@presupuestos_habilitados
@require_POST
def anular_presupuesto(request, presupuesto_id):
    p = get_object_or_404(Presupuesto, id=presupuesto_id, empresa=request.user.empresa)
    p.estado = 'anulado'
    p.save(update_fields=['estado'])
    return redirect('detalle_presupuesto', presupuesto_id=p.id)


@presupuestos_habilitados
@require_POST
def cancelar_borrador(request):
    for k in SESSION_KEYS:
        request.session.pop(k, None)
    return redirect('nuevo_presupuesto')

@presupuestos_habilitados
@require_POST
def convertir_a_venta(request, presupuesto_id):
    p = get_object_or_404(Presupuesto, id=presupuesto_id, empresa=request.user.empresa)

    if p.estado != 'vigente':
        messages.error(request, 'Solo se pueden convertir presupuestos vigentes.')
        return redirect('detalle_presupuesto', presupuesto_id=p.id)

    carrito = []
    omitidos = []
    for d in p.detalles.select_related('producto'):
        prod = d.producto
        if not prod or not prod.activo:
            omitidos.append(d.descripcion)
            continue

        es_caja = bool(d.metros_por_caja)
        item = {
            'producto_id': prod.id,
            'nombre': d.descripcion,
            'cantidad': float(d.cantidad),
            'precio_unitario': float(d.precio_unitario),
            'subtotal': float(d.cantidad * d.precio_unitario),
            'descuento': 0,
            'tipo_precio': 'caja' if es_caja else None,
            'ahorro_unitario': 0,
            'venta_por_caja': es_caja,
        }
        if es_caja:
            item['metros_por_caja'] = float(d.metros_por_caja)
            item['metros_totales'] = float(d.metros_totales or d.cantidad * d.metros_por_caja)
            item['precio_m2'] = float(d.precio_m2) if d.precio_m2 else None
        carrito.append(item)

    if not carrito:
        messages.error(request, 'Ningún producto del presupuesto está disponible para vender.')
        return redirect('detalle_presupuesto', presupuesto_id=p.id)

    s = request.session
    s['carrito'] = carrito
    s['cliente_id'] = str(p.cliente_id) if p.cliente_id else None
    s['cuenta_corriente'] = False
    s['nota'] = (f'Presupuesto #{p.numero_empresa:06d}'
                 + (f' - {p.nota}' if p.nota else ''))
    s['presupuesto_origen_id'] = p.id
    if request.user.empresa.usa_venta_por_caja:
        s['tipo_comprobante'] = 'a4'
    s.modified = True

    if omitidos:
        messages.warning(request, 'No se cargaron (inactivos/eliminados): ' + ', '.join(omitidos))
    if p.vencido:
        messages.warning(request, 'Atención: el presupuesto está vencido, revisá los precios.')
    return redirect('nueva_venta')