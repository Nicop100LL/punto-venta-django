from decimal import Decimal, InvalidOperation, ROUND_CEILING
from functools import wraps

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
    presupuestos = (Presupuesto.objects
                    .filter(empresa=request.user.empresa)
                    .select_related('cliente', 'usuario')[:200])
    return render(request, 'presupuestos/lista_presupuestos.html',
                  {'presupuestos': presupuestos})


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