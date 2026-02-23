from decimal import Decimal
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from productos.models import Producto
from .models import Venta, DetalleVenta, Cliente
from .forms import VentaForm, DetalleVentaForm
from django.http import JsonResponse
from django.http import HttpResponse
from django.template.loader import get_template
from .models import PagoCliente
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.utils.timezone import now
from reportlab.lib.units import cm
from .models import Venta
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.http import urlencode
from django.db.models import Sum, Count, Avg
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from decimal import Decimal
from urllib.parse import urlencode
from .forms import VentaForm, DetalleVentaForm
from productos.models import Producto
from .models import DetalleVenta
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from urllib.parse import urlencode
from .models import Producto, DetalleVenta
from .forms import VentaForm, DetalleVentaForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Venta
from .forms import ClienteForm
from django.http import JsonResponse
from .models import Producto
import math
from caja.utils import get_caja_abierta
from decimal import Decimal
from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Producto, DetalleVenta, Cliente
from .forms import VentaForm, DetalleVentaForm
from django.contrib import messages
from .models import Venta, DetalleVenta, Cliente, NotaCredito, DetalleNotaCredito





@login_required
def nueva_venta(request):
    """
    Vista principal de ventas:
    - Maneja carrito por sesión
    - Permite agregar/eliminar productos
    - Guarda cliente en sesión
    - Finaliza venta y actualiza saldo si es cuenta corriente
    """
    PRODUCTO_VARIOS_CODIGO = '1010'


    # =========================
    # CAJA ABIERTA (solo detección)
    # =========================
    caja_abierta = get_caja_abierta(
        request.user,
        request.user.empresa
    )
    # =========================
    # MODAL ABRIR CAJA (solo empleados)
    # =========================
    abrir_modal_caja = False
    if request.user.es_empleado and not caja_abierta:
        abrir_modal_caja = True

        
    # =========================
    # INICIALIZACIÓN DE SESIÓN
    # =========================
    if 'carrito' not in request.session:
        request.session['carrito'] = []

    carrito = request.session['carrito']
    tipo_comprobante = request.session.get('tipo_comprobante', 'ticket')
    tipo_pago = request.session.get('tipo_pago', 'EF')
    cliente_id = request.session.get('cliente_id')
    cuenta_corriente = request.session.get('cuenta_corriente', False)

    # Convertimos cliente_id a int si es válido
    try:
        cliente_id_int = int(cliente_id) if cliente_id not in (None, '', 'None') else None
    except (TypeError, ValueError):
        cliente_id_int = None

    # =========================
    # POST
    # =========================
    if request.method == 'POST':

        # -------------------------
        # GUARDAR CLIENTE EN SESIÓN
        # -------------------------
        cliente_post = request.POST.get('cliente')
        request.session['cliente_id'] = cliente_post if cliente_post not in (None, '', 'None') else None

        # -------------------------
        # GUARDAR CONFIGURACIÓN
        # -------------------------
        tipo_pago = request.POST.get('tipo_pago', 'EF')
        tipo_comprobante = request.POST.get('tipo_comprobante', 'ticket')
        cuenta_corriente = request.POST.get('cuenta_corriente') == 'on'

        request.session['tipo_pago'] = tipo_pago
        request.session['tipo_comprobante'] = tipo_comprobante
        request.session['cuenta_corriente'] = cuenta_corriente
        request.session['nota'] = request.POST.get('nota', '')

        # =========================
        # AGREGAR PRODUCTO
        # =========================
        if 'agregar' in request.POST:
            codigo = request.POST.get('codigo')
            cantidad = Decimal(request.POST.get('cantidad', '1'))
            precio_manual = request.POST.get('precio_unitario')

            try:
                producto = Producto.objects.get(
                    codigo=codigo,
                    empresa=request.user.empresa
                )

                item = next(
                    (i for i in carrito if i['producto_id'] == producto.id),
                    None
                )

                # Calculamos precio con descuento
                def calcular_precio(cant):
                    # 🔥 PRODUCTO VARIOS → precio manual, sin descuento
                    if producto.codigo == PRODUCTO_VARIOS_CODIGO and precio_manual:
                        return Decimal(precio_manual), 0

                    # Productos normales con descuento
                    if (
                        producto.aplica_descuento and
                        producto.cantidad_minima_descuento and
                        cant >= producto.cantidad_minima_descuento
                    ):
                        return (
                            producto.precio_venta * (1 - producto.porcentaje_descuento / 100),
                            producto.porcentaje_descuento
                        )

                    return producto.precio_venta, 0


                if item and producto.codigo != PRODUCTO_VARIOS_CODIGO:

                    item['cantidad'] += float(cantidad)
                    precio, descuento = calcular_precio(item['cantidad'])
                    item['precio_unitario'] = float(precio)
                    item['subtotal'] = item['cantidad'] * item['precio_unitario']
                    item['descuento'] = float(descuento)
                else:
                    precio, descuento = calcular_precio(cantidad)
                    item_dict = {
                        'producto_id': producto.id,
                        'nombre': producto.nombre,
                        'precio_unitario': float(precio),
                        'cantidad': float(cantidad),
                        'subtotal': float(precio * cantidad),
                        'descuento': float(descuento),
                    }

                    # 🔹 Agregamos codigo_unico solo para VARIOS
                    if producto.codigo == PRODUCTO_VARIOS_CODIGO:
                        item_dict['codigo_unico'] = request.POST.get('codigo_unico_varios')

                    carrito.append(item_dict)


                request.session['carrito'] = carrito
                request.session.modified = True
                return redirect('nueva_venta')

            except Producto.DoesNotExist:
                pass  # se maneja abajo en render

        # =========================
        # ELIMINAR PRODUCTO
        # =========================
        elif 'eliminar_codigo_unico' in request.POST:
            # Borrar un producto VARIOS por su código único
            codigo_unico = request.POST.get('eliminar_codigo_unico')
            request.session['carrito'] = [
                i for i in carrito if i.get('codigo_unico') != codigo_unico
            ]
            request.session.modified = True
            return redirect('nueva_venta')

        elif 'eliminar_codigo' in request.POST:
            # Borrar productos normales por producto_id
            producto_id = int(request.POST.get('eliminar_codigo'))
            request.session['carrito'] = [
                i for i in carrito if i['producto_id'] != producto_id
            ]
            request.session.modified = True
            return redirect('nueva_venta')


        # =========================
        # FINALIZAR VENTA
        # =========================
        elif 'finalizar' in request.POST:
            print("POST FINALIZAR:", request.POST)
             # 🔒 BLOQUEAR VENTA SIN CAJA solo para empleados
            if request.user.es_empleado and not caja_abierta:
                abrir_modal_caja = True  # activamos modal
                venta_form = VentaForm(initial={'cliente': cliente_id_int})
                venta_form.fields['cliente'].queryset = Cliente.objects.filter(
                    empresa=request.user.empresa
                )
                # PASAMOS TODAS LAS VARIABLES EXISTENTES
                return render(request, 'ventas/nueva_venta.html', {
                    'venta_form': venta_form,
                    'detalle_form': DetalleVentaForm(),
                    'carrito': carrito,
                    'total': sum(float(i['subtotal']) for i in carrito),
                    'tipo_comprobante': tipo_comprobante,
                    'cliente_id': cliente_id_int,
                    'cuenta_corriente': cuenta_corriente,
                    'saldo_cliente': None if cliente_id_int is None else Cliente.objects.filter(id=cliente_id_int).first().saldo,
                    'tipo_pago': tipo_pago,
                    'abrir_modal_caja': abrir_modal_caja,
                    'caja_abierta': caja_abierta,
                })
            
            venta_form = VentaForm(request.POST)
            venta_form.fields['cliente'].queryset = Cliente.objects.filter(
                empresa=request.user.empresa
            )

            if venta_form.is_valid() and carrito:
                venta = venta_form.save(commit=False)
                venta.nota = request.POST.get('nota', '')
                venta.usuario = request.user
                venta.empresa = request.user.empresa
                
                venta.importe_entregado = (
                    Decimal(request.POST.get('importe_entregado'))
                    if request.POST.get('importe_entregado')
                    else None
                )

                venta.vuelto = (
                    Decimal(request.POST.get('vuelto'))
                    if request.POST.get('vuelto')
                    else None
                )
                
                venta.caja = caja_abierta
                venta.total = sum(Decimal(str(i['subtotal'])) for i in carrito)
                venta.tipo_comprobante = tipo_comprobante
                venta.tipo_pago = tipo_pago
                venta.cuenta_corriente = cuenta_corriente

                # Asignar cliente desde sesión
                cliente = None
                if request.session.get('cliente_id'):
                    try:
                        cliente = Cliente.objects.get(
                            id=int(request.session['cliente_id'])
                        )
                        venta.cliente = cliente
                    except Cliente.DoesNotExist:
                        venta.cliente = None

                # Numeración por empresa
                ultima = Venta.objects.filter(
                    empresa=request.user.empresa
                ).order_by('-numero_empresa').first()
                venta.numero_empresa = (ultima.numero_empresa + 1) if ultima else 1

                venta.save()

                # 🔥 SALDO: UNA SOLA VEZ
                if cuenta_corriente and cliente:
                    cliente.saldo += venta.total
                    cliente.save()

                # Detalle y stock
                for item in carrito:
                    producto = Producto.objects.get(id=item['producto_id'])

                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=item['cantidad'],
                        precio_unitario=item['precio_unitario']
                    )

                # 🔥 NO descontar stock para VARIOS
                if producto.codigo != PRODUCTO_VARIOS_CODIGO:
                    producto.stock_actual -= Decimal(str(item['cantidad']))
                    producto.save()



                # Limpiar sesión
                for key in ('carrito', 'cliente_id', 'tipo_pago', 'tipo_comprobante', 'cuenta_corriente'):
                    request.session.pop(key, None)
                request.session.pop('nota', None)
                

                return redirect(
                    f"{reverse('detalle_venta', args=[venta.id])}?tipo={tipo_comprobante}"
                )

    # =========================
    # GET
    # =========================
    cliente = None
    saldo_cliente = None

    if cliente_id_int:
        try:
            cliente = Cliente.objects.get(id=cliente_id_int)
            saldo_cliente = cliente.saldo
        except Cliente.DoesNotExist:
            pass

    venta_form = VentaForm(initial={'cliente': cliente_id_int})
    venta_form.fields['cliente'].queryset = Cliente.objects.filter(
        empresa=request.user.empresa
    )

    return render(request, 'ventas/nueva_venta.html', {
        'venta_form': venta_form,
        'detalle_form': DetalleVentaForm(),
        'carrito': carrito,
        'total': sum(float(i['subtotal']) for i in carrito),
        'tipo_comprobante': tipo_comprobante,
        'cliente_id': cliente_id_int,
        'cuenta_corriente': cuenta_corriente,
        'saldo_cliente': saldo_cliente,
        'tipo_pago': tipo_pago,
        'abrir_modal_caja': abrir_modal_caja,
        'caja_abierta': caja_abierta,

    })



from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import Venta

@login_required
def lista_ventas(request):
    Usuario = get_user_model()

    # Obtener el filtro de usuario desde GET (si existe)
    usuario_id = request.GET.get('usuario')

    # Obtener el filtro de fecha desde GET (si existe)
    fecha_str = request.GET.get('fecha')
    
    if fecha_str:
        # Convertimos la fecha de string a date
        try:
            fecha = timezone.datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha = None
    else:
        fecha = None

    # Filtramos ventas por empresa
    ventas = Venta.objects.filter(empresa=request.user.empresa)

    # Si no se seleccionó fecha, tomamos el último día con ventas
    if not fecha:
        ultima_venta = ventas.order_by('-fecha').first()
        fecha = ultima_venta.fecha.date() if ultima_venta else timezone.localdate()

    # Filtramos por fecha
    ventas = ventas.filter(fecha__date=fecha)

    # Filtramos por usuario si se seleccionó
    if usuario_id:
        ventas = ventas.filter(usuario_id=usuario_id)

    # Obtener usuarios de la empresa
    usuarios = Usuario.objects.filter(empresa=request.user.empresa)

    return render(request, 'ventas/lista_ventas.html', {
        'ventas': ventas,
        'usuarios': usuarios,
        'usuario_seleccionado': usuario_id or '',
        'fecha': fecha,  # enviamos la fecha al template
    })

@login_required
def detalle_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, empresa=request.user.empresa)

    if venta.tipo_comprobante == 'factura_afip':
        total = float(venta.total)
        neto = round(total / 1.21, 2)
        iva = round(total - neto, 2)
        template = 'ventas/detalle_factura_afip.html'
    else:
        neto = None
        iva = None
        template = 'ventas/detalle_ticket.html'

        # ✅ Contar productos: al menos 1 por línea, más si la cantidad entera >1
    total_productos = sum(max(1, int(item.cantidad)) for item in venta.detalles.all())

    return render(request, template, {
        'venta': venta,
        'neto': neto,
        'iva': iva,
        'total_productos': total_productos,
        'empresa': request.user.empresa,
    })

@login_required
def venta_pdf(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, empresa=request.user.empresa)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=venta_{venta.id}.pdf'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    p.setFont("Helvetica-Bold", 16)
    p.drawString(2 * cm, y, f"Factura de Venta #{venta.numero_empresa}")
    y -= 1.5 * cm

    p.setFont("Helvetica", 12)
    p.drawString(2 * cm, y, f"Fecha: {venta.fecha.strftime('%d/%m/%Y %H:%M')}")
    y -= 0.7 * cm
    p.drawString(2 * cm, y, f"Vendedor: {venta.usuario.get_full_name() or venta.usuario.username}")
    y -= 0.7 * cm
    p.drawString(2 * cm, y, f"Cliente: {venta.cliente.nombre if venta.cliente else '-'}")
    y -= 1.2 * cm

    p.setFont("Helvetica-Bold", 11)
    p.drawString(2 * cm, y, "Producto")
    p.drawString(9 * cm, y, "Cantidad")
    p.drawString(12 * cm, y, "Precio Unit.")
    p.drawString(16 * cm, y, "Subtotal")
    y -= 0.5 * cm
    p.line(2 * cm, y, width - 2 * cm, y)
    y -= 0.5 * cm

    p.setFont("Helvetica", 10)
    for item in venta.detalles.all():
        if y < 3 * cm:
            p.showPage()
            y = height - 2 * cm
        p.drawString(2 * cm, y, item.producto.nombre if item.producto else "Producto eliminado")
        p.drawRightString(11 * cm, y, f"{item.cantidad}")
        p.drawRightString(15 * cm, y, f"${item.precio_unitario:.2f}")
        p.drawRightString(19 * cm, y, f"${item.subtotal():.2f}")
        y -= 0.5 * cm

    y -= 1 * cm
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(19 * cm, y, f"TOTAL: ${venta.total:.2f}")

    p.showPage()
    p.save()
    return response

@login_required
def lista_clientes(request):
    clientes = Cliente.objects.filter(empresa=request.user.empresa)
    return render(request, 'ventas/lista_clientes.html', {'clientes': clientes})

from django.http import JsonResponse

@login_required
def nuevo_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.empresa = request.user.empresa
            cliente.save()
            return JsonResponse({
                'success': True,
                'cliente': {
                    'id': cliente.id,
                    'nombre': cliente.nombre,
                    'cuit': cliente.cuit or '',
                    'condicion_iva': cliente.get_condicion_iva_display(),
                    'direccion': cliente.direccion or '',
                    'saldo': float(cliente.saldo or 0),
                }
            })
        else:
            print(form.errors)
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

from django.http import JsonResponse
from .models import Cliente
 
@login_required
def editar_cliente(request):
    if request.method == 'POST':
        try:
            cliente_id = request.POST.get('cliente_id')
            if not cliente_id:
                return JsonResponse({'success': False, 'error': 'ID de cliente no proporcionado'}, status=400)

            cliente = Cliente.objects.get(id=cliente_id)

            cliente.nombre = request.POST.get('nombre', '')
            cliente.cuit = request.POST.get('cuit', '')
            cliente.condicion_iva = request.POST.get('condicion_iva', '')
            cliente.direccion = request.POST.get('direccion', '')
            cliente.save()

            return JsonResponse({
                'success': True,
                'cliente': {
                    'id': cliente.id,
                    'nombre': cliente.nombre,
                    'cuit': cliente.cuit,
                    'get_condicion_iva_display': cliente.get_condicion_iva_display(),
                    'direccion': cliente.direccion,
                    'saldo': cliente.saldo
                }
            })

        except Cliente.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cliente no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

@login_required
def obtener_saldo_cliente(request):
    cliente_id = request.GET.get('cliente_id')
    try:
        cliente = Cliente.objects.get(id=cliente_id, empresa=request.user.empresa)
        return JsonResponse({'saldo': float(cliente.saldo)})
    except Cliente.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Cliente, PagoCliente  # Asegurate de tener este import

@login_required
def modificar_saldo_cliente(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        tipo_pago = request.POST.get('tipo_pago')

        try:
            cliente = Cliente.objects.get(pk=cliente_id)

            monto_pago_realizado = None

            if tipo_pago == "total":
                monto_pago_realizado = cliente.saldo
                cliente.saldo = 0

            elif tipo_pago == "parcial":
                try:
                    monto_pago = Decimal(request.POST.get('monto_pago') or "0")
                except:
                    return JsonResponse({"success": False, "error": "Monto inválido."})

                if monto_pago <= 0:
                    return JsonResponse({"success": False, "error": "El monto debe ser mayor a cero."})

                if monto_pago > cliente.saldo:
                    return JsonResponse({"success": False, "error": "El monto supera el saldo del cliente."})

                cliente.saldo -= monto_pago
                monto_pago_realizado = monto_pago

            else:
                return JsonResponse({"success": False, "error": "Tipo de pago inválido."})

            cliente.save()

            # 🔹 Registrar el pago si hubo uno
            if monto_pago_realizado and monto_pago_realizado > 0:
                PagoCliente.objects.create(
                    cliente=cliente,
                    monto=monto_pago_realizado,
                    usuario=request.user
                )

            return JsonResponse({
                "success": True,
                "cliente": {
                    "id": cliente.id,
                    "saldo": float(cliente.saldo)
                }
            })

        except Cliente.DoesNotExist:
            return JsonResponse({"success": False, "error": "Cliente no encontrado."})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido."})

@login_required
def historial_pagos_cliente(request, cliente_id):
    pagos = PagoCliente.objects.filter(cliente_id=cliente_id).order_by('-fecha')

    data = [
        {
            'fecha': pago.fecha.strftime('%Y-%m-%d %H:%M'),
            'monto': str(pago.monto),
            'tipo': pago.tipo,
            'usuario': pago.usuario.username if pago.usuario else 'N/A',
        }
        for pago in pagos
    ]
    return JsonResponse({'success': True, 'pagos': data})

@login_required
def eliminar_cliente(request):
    cliente_id = request.POST.get('cliente_id')
    try:
        cliente = Cliente.objects.get(id=cliente_id)
        cliente.delete()
        return JsonResponse({'success': True})
    except Cliente.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Cliente no encontrado'})


@login_required
def estadisticas_ventas(request):
    hoy = now().date()
    inicio_mes = hoy.replace(day=1)

    ventas_mes = Venta.objects.filter(
        fecha__date__gte=inicio_mes,
        fecha__date__lte=hoy,
        empresa=request.user.empresa
    )

    total_ventas = ventas_mes.aggregate(total=Sum('total'))['total'] or 0
    cantidad_ventas = ventas_mes.count()
    ticket_promedio = ventas_mes.aggregate(avg=Avg('total'))['avg'] or 0

    # Agrupamos por día
    ventas_por_dia = (
        ventas_mes.extra({'dia': "DATE(fecha)"}).values('dia')
        .annotate(total=Sum('total'))
        .order_by('dia')
    )

    return render(request, 'ventas/estadisticas.html', {
        'total_ventas': total_ventas,
        'cantidad_ventas': cantidad_ventas,
        'ticket_promedio': ticket_promedio,
        'ventas_por_dia': ventas_por_dia,
    })
    
    # views.py

@login_required
def buscar_producto_por_nombre(request):
    q = request.GET.get('q', '').strip()
    empresa = request.user.empresa  # 🔹 filtramos por empresa

    if len(q) < 2:
        return JsonResponse([], safe=False)

    productos = (
        Producto.objects
        .filter(nombre__icontains=q, empresa=empresa)  # 🔹 agregamos empresa
        .order_by('nombre')[:10]  # limitar a 10 resultados
    )

    data = []
    for p in productos:
        data.append({
            'id': p.id,
            'codigo': p.codigo,
            'nombre': p.nombre,
            'precio': float(p.precio_venta),
            'tipo_venta': p.tipo_venta,
        })

    return JsonResponse(data, safe=False)


@login_required
def crear_nota_credito(request, venta_id):
    venta = get_object_or_404(
        Venta,
        id=venta_id,
        empresa=request.user.empresa
    )
    cliente = venta.cliente

    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')

        caja_para_nota = getattr(venta, 'caja', None)
        if caja_para_nota and caja_para_nota.estado != 'abierta':
            caja_para_nota = None

        nota = NotaCredito.objects.create(
            venta=venta,
            cliente=cliente,
            motivo=motivo,
            usuario=request.user,
            caja=caja_para_nota,
            estado='aplicada'
        )

        total_nota = Decimal('0')

        for detalle in venta.detalles.all():
            cant_str = request.POST.get(f'cantidad_{detalle.id}', '0')
            cantidad = Decimal(cant_str or '0')

            if cantidad <= 0:
                continue

            subtotal = detalle.precio_unitario * cantidad

            ya_devuelto = DetalleNotaCredito.objects.filter(
                nota_credito__venta=venta,
                producto=detalle.producto
            ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')

            if cantidad + ya_devuelto > detalle.cantidad:
                continue

            DetalleNotaCredito.objects.create(
                nota_credito=nota,
                producto=detalle.producto,
                cantidad=cantidad,
                precio_unitario=detalle.precio_unitario,
                subtotal=subtotal
            )

            total_nota += subtotal

        nota.total = total_nota
        nota.save()

        if cliente:
            cliente.saldo -= total_nota
            cliente.save()

        return redirect('detalle_venta', venta_id=venta.id)

    detalles = []
    for detalle in venta.detalles.all():
        ya_devuelto = DetalleNotaCredito.objects.filter(
            nota_credito__venta=venta,
            producto=detalle.producto
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
        disponible = detalle.cantidad - ya_devuelto

        detalles.append({
            'detalle': detalle,
            'ya_devuelto': ya_devuelto,
            'disponible': disponible
        })

    return render(request, 'ventas/crear_nota_credito.html', {
        'venta': venta,
        'cliente': cliente,
        'detalles': detalles
    })


@login_required
def detalle_nota_credito(request, pk):
    nota = get_object_or_404(
        NotaCredito,
        pk=pk,
        venta__empresa=request.user.empresa
    )

    

    return render(
        request,
        'ventas/detalle_nota_credito.html',
        {
            'nota': nota,
            'empresa': request.user.empresa,
        }
    )


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Venta
from impresoras.models import ConfiguracionImpresoraTicket

def enviar_ticket(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)

    try:
        config = venta.empresa.config_impresora_ticket
    except ConfiguracionImpresoraTicket.DoesNotExist:
        # Fallback clásico a print()
        return JsonResponse({"status": "fallback"})

    if config.microservicio_url:
        # Aquí harías fetch al microservicio desde Django
        # O desde JS, depende de la arquitectura
        return JsonResponse({"status": "ok"})
    else:
        # No hay microservicio configurado
        return JsonResponse({"status": "fallback"})


from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm as mm_unit

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase import pdfdoc

def draw_wrapped_text(canvas, text, x, y, max_width, font="Helvetica", size=8, leading=3):
    canvas.setFont(font, size)

    words = text.split(" ")
    line = ""
    lines = []

    for word in words:
        test = f"{line} {word}".strip()
        if stringWidth(test, font, size) <= max_width:
            line = test
        else:
            lines.append(line)
            line = word

    if line:
        lines.append(line)

    for l in lines:
        canvas.drawString(x, y, l)
        y -= leading * mm

    return y

@login_required
def ticket_pdf_prueba(request, venta_id):
    venta = get_object_or_404(
        Venta,
        id=venta_id,
        empresa=request.user.empresa
    )

    # Tamaño 80mm x alto dinámico
    ancho = 80 * mm
    alto = 160 * mm  # alto grande, luego "se corta solo"

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=ticket_prueba.pdf"

    c = canvas.Canvas(response, pagesize=(ancho, alto))
    y = alto - 4 * mm

    # ===== ENCABEZADO =====
    empresa = venta.empresa

    if empresa.logo:
        try:
            c.drawImage(
                empresa.logo.path,
                25 * mm, y - 20 * mm,
                width=30 * mm,
                preserveAspectRatio=True,
                mask='auto'
            )
            y -= 22 * mm
        except:
            pass

    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(40 * mm, y, empresa.nombre)
    y -= 6 * mm

    c.setFont("Helvetica", 8)
    c.drawCentredString(40 * mm, y, f"Venta #{venta.numero_empresa}")
    y -= 6 * mm

    # ===== DATOS =====
    c.drawString(5 * mm, y, f"Fecha: {venta.fecha:%d/%m/%Y %H:%M}")
    y -= 4 * mm

    vendedor = venta.usuario.get_full_name() or venta.usuario.username
    c.drawString(5 * mm, y, f"Vendedor: {vendedor}")
    y -= 4 * mm

    cliente = venta.cliente.nombre if venta.cliente else "Consumidor Final"
    c.drawString(5 * mm, y, f"Cliente: {cliente}")
    y -= 6 * mm

    # ===== LINEA =====
    c.line(5 * mm, y, 75 * mm, y)
    y -= 4 * mm

    # ===== CABECERA PRODUCTOS =====
    c.setFont("Helvetica-Bold", 8)
    c.drawString(5 * mm, y, "Prod.")
    c.drawRightString(35 * mm, y, "Cant")
    c.drawRightString(55 * mm, y, "P.Unit")
    c.drawRightString(75 * mm, y, "Subt")
    y -= 4 * mm

    c.line(5 * mm, y, 75 * mm, y)
    y -= 3 * mm

    # ===== ITEMS =====
    c.setFont("Helvetica", 8)

    for item in venta.detalles.all():
        nombre = item.producto.nombre if item.producto else "Producto eliminado"
        y_inicial = y

        y = draw_wrapped_text(
            c,
            nombre,
            x=5 * mm,
            y=y,
            max_width=23 * mm,  # ancho real columna producto
            font="Helvetica",
            size=8,
            leading=3
        )

        c.drawRightString(35 * mm, y_inicial, str(item.cantidad))
        c.drawRightString(55 * mm, y_inicial, f"{item.precio_unitario:.2f}")
        c.drawRightString(75 * mm, y_inicial, f"{item.subtotal():.2f}")

        y -= 2 * mm  # espacio entre productos

    # ===== TOTALES =====
    y -= 4 * mm
    c.line(5 * mm, y, 75 * mm, y)
    y -= 4 * mm

    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(75 * mm, y, f"TOTAL: ${venta.total:.2f}")

    # ===== FIN =====
    c.showPage()

    # METADATA (esto sí es válido)
    c.setAuthor("POS")
    c.setTitle("Ticket de venta")
    

    c.save()

    return response