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
from reportlab.lib.units import cm
from .models import Venta
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.http import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from decimal import Decimal
from urllib.parse import urlencode
from .forms import VentaForm, DetalleVentaForm
from productos.models import Producto
from .models import DetalleVenta

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


from decimal import Decimal
from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Producto, DetalleVenta, Cliente
from .forms import VentaForm, DetalleVentaForm


@login_required
def nueva_venta(request):
    # Inicializamos el carrito si no existe en la sesión
    if 'carrito' not in request.session:
        request.session['carrito'] = []

    carrito = request.session['carrito']
    tipo_comprobante = request.session.get('tipo_comprobante', 'ticket')
    tipo_pago = request.session.get('tipo_pago', 'EF')
    cliente_id = request.session.get('cliente_id')

    # Validamos y convertimos cliente_id a int si es posible
    if cliente_id and cliente_id != 'Ninguno':
        try:
            cliente_id_int = int(cliente_id)
        except (TypeError, ValueError):
            cliente_id_int = None
    else:
        cliente_id_int = None

    # Si se envía el formulario por POST
    if request.method == 'POST':
        tipo_pago = request.POST.get('tipo_pago', 'EF')
        tipo_comprobante = request.POST.get('tipo_comprobante', 'ticket')
        cuenta_corriente = request.POST.get('cuenta_corriente') == 'on'
        cliente_id = request.POST.get('cliente')

        # Guardamos en sesión los datos seleccionados
        request.session['tipo_pago'] = tipo_pago
        request.session['tipo_comprobante'] = tipo_comprobante
        request.session['cuenta_corriente'] = cuenta_corriente
        request.session['cliente_id'] = cliente_id if cliente_id not in (None, '', 'None') else None

        # Intentamos convertir el cliente_id a int
        try:
            cliente_id_int = int(request.session['cliente_id'])
        except (TypeError, ValueError):
            cliente_id_int = None

        # Acción: Agregar producto al carrito
        if 'agregar' in request.POST:
         # Obtener el código del producto y la cantidad solicitada desde el formulario
            codigo = request.POST.get('codigo')
            cantidad = Decimal(request.POST.get('cantidad', '1'))  # Si no se proporciona cantidad, se toma como 1

            try:
             # Buscamos el producto por su código y la empresa asociada
                producto = Producto.objects.get(codigo=codigo, empresa=request.user.empresa)

                # Inicializamos el subtotal en caso de que no haya descuento
                subtotal = producto.precio_venta * cantidad

                # Verificamos si el producto ya está en el carrito
                producto_en_carrito = next((item for item in carrito if item['producto_id'] == producto.id), None)

                # Si el producto ya existe en el carrito, actualizamos la cantidad y el subtotal
                if producto_en_carrito:
                    # Actualizamos la cantidad en el carrito
                    producto_en_carrito['cantidad'] += float(cantidad)

                    # Verificamos si el producto tiene un descuento por cantidad
                    descuento_aplicado = 0  # Si no tiene descuento
                    if producto.aplica_descuento and producto_en_carrito['cantidad'] >= producto.cantidad_minima_descuento:
                        # Si aplica descuento por cantidad, calculamos el descuento y el precio unitario
                        descuento_aplicado = producto.porcentaje_descuento
                        precio_unitario = producto.precio_venta * (1 - descuento_aplicado / 100)
                    else:
                        # Si no aplica descuento, mantenemos el precio unitario original
                        precio_unitario = producto.precio_venta

                    # Actualizamos el subtotal con el nuevo precio unitario
                    producto_en_carrito['precio_unitario'] = float(precio_unitario)
                    producto_en_carrito['subtotal'] = producto_en_carrito['cantidad'] * producto_en_carrito['precio_unitario']
                    producto_en_carrito['descuento'] = float(descuento_aplicado)

                # Si el producto no existe en el carrito, lo agregamos como nuevo ítem
                else:
                    # Si el producto tiene descuento, lo calculamos
                    descuento_aplicado = 0  # Si no tiene descuento
                    if producto.aplica_descuento and cantidad >= producto.cantidad_minima_descuento:
                        # Si aplica descuento por cantidad, calculamos el descuento y el precio unitario
                        descuento_aplicado = producto.porcentaje_descuento
                        precio_unitario = producto.precio_venta * (1 - descuento_aplicado / 100)
                    else:
                        # Si no aplica descuento, mantenemos el precio unitario original
                        precio_unitario = producto.precio_venta

                    # Agregamos el producto al carrito con el descuento aplicado
                    carrito.append({
                        'producto_id': producto.id,
                        'nombre': producto.nombre,
                        'precio_unitario': float(precio_unitario),
                        'cantidad': float(cantidad),
                        'subtotal': float(precio_unitario * cantidad),
                        'descuento': float(descuento_aplicado),  # Guardamos el descuento aplicado
                    })

                # Guardamos el carrito actualizado en la sesión
                request.session['carrito'] = carrito
                request.session.modified = True

            except Producto.DoesNotExist:
                # Si el producto no se encuentra, mostramos mensaje de error
                total = sum(float(item['subtotal']) for item in carrito)
                venta_form = VentaForm(initial={'cliente': cliente_id_int})  # ← CORREGIDO
                return render(request, 'ventas/nueva_venta.html', {
                    'venta_form': venta_form,
                    'detalle_form': DetalleVentaForm(),
                    'carrito': carrito,
                    'total': total,
                    'cliente_id': cliente_id_int,
                    'saldo_cliente': None,
                    'tipo_comprobante': tipo_comprobante,
                    'cuenta_corriente': cuenta_corriente,
                    'tipo_pago': tipo_pago,
                    'error': "Producto no encontrado",
                })

            return redirect('nueva_venta')

        # Acción: Eliminar producto del carrito
        elif 'eliminar_codigo' in request.POST:
            producto_id = int(request.POST.get('eliminar_codigo'))
            carrito = [item for item in carrito if item['producto_id'] != producto_id]
            request.session['carrito'] = carrito
            request.session.modified = True
            return redirect('nueva_venta')

        # Acción: Finalizar y guardar la venta
        elif 'finalizar' in request.POST:
            venta_form = VentaForm(request.POST)
            cuenta_corriente_activada = cuenta_corriente

            if venta_form.is_valid() and carrito:
                venta = venta_form.save(commit=False)
                venta.usuario = request.user
                venta.empresa = request.user.empresa
                venta.total = sum(Decimal(str(item['subtotal'])) for item in carrito)
                venta.tipo_comprobante = tipo_comprobante
                venta.cuenta_corriente = cuenta_corriente_activada
                venta.tipo_pago = tipo_pago

                if request.session.get('cliente_id') not in (None, '', 'None'):
                    venta.cliente_id = int(request.session['cliente_id'])

                venta.save()

                # Si se usa cuenta corriente, actualizamos saldo
                if cuenta_corriente_activada and venta.cliente:
                    venta.cliente.saldo += venta.total
                    venta.cliente.save()

                # Guardamos el detalle de venta
                for item in carrito:
                    producto = Producto.objects.get(id=item['producto_id'])
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=item['cantidad'],
                        precio_unitario=item['precio_unitario']
                    )
                    producto.stock_actual -= Decimal(str(item['cantidad']))
                    producto.save()

                # Limpiamos la sesión
                request.session['carrito'] = []
                request.session.pop('tipo_comprobante', None)
                request.session.pop('cliente_id', None)
                request.session.pop('tipo_pago', None)
                request.session.pop('cuenta_corriente', None)
                request.session.modified = True

                query_string = urlencode({'tipo': tipo_comprobante})
                url = reverse('detalle_venta', args=[venta.id])
                return redirect(f"{url}?{query_string}")

            else:
                # Si hay errores en el formulario
                print("Formulario no válido:", venta_form.errors)
                return render(request, 'ventas/nueva_venta.html', {
                    'venta_form': venta_form,
                    'detalle_form': DetalleVentaForm(),
                    'carrito': carrito,
                    'total': sum(float(item['subtotal']) for item in carrito),
                    'tipo_comprobante': tipo_comprobante,
                    'cliente_id': cliente_id_int,
                    'cuenta_corriente': cuenta_corriente_activada,
                    'saldo_cliente': None,
                    'tipo_pago': tipo_pago,
                    'error': 'El formulario tiene errores.',
                })

    # Si es GET u otra cosa, preparamos los datos iniciales
    cliente = None
    saldo_cliente = None

    if cliente_id_int:
        try:
            cliente = Cliente.objects.get(id=cliente_id_int)
            saldo_cliente = cliente.saldo
        except Cliente.DoesNotExist:
            saldo_cliente = None

    return render(request, 'ventas/nueva_venta.html', {
        'venta_form': VentaForm(initial={'cliente': cliente_id_int}),
        'detalle_form': DetalleVentaForm(),
        'carrito': carrito,
        'total': sum(float(item['subtotal']) for item in carrito),
        'tipo_comprobante': tipo_comprobante,
        'cliente_id': cliente_id_int,
        'cuenta_corriente': request.session.get('cuenta_corriente', False),
        'saldo_cliente': saldo_cliente,
        'tipo_pago': tipo_pago,
    })

from django.contrib.auth import get_user_model

@login_required
def lista_ventas(request):
    ventas = Venta.objects.filter(empresa=request.user.empresa).order_by('-fecha')

    # Obtener el filtro de usuario desde GET (si existe)
    usuario_id = request.GET.get('usuario')
    if usuario_id:
        ventas = ventas.filter(usuario_id=usuario_id)

    # Obtener la lista de usuarios de la empresa para el selector
    Usuario = get_user_model()
    usuarios = Usuario.objects.filter(empresa=request.user.empresa)

    return render(request, 'ventas/lista_ventas.html', {
        'ventas': ventas,
        'usuarios': usuarios,
        'usuario_seleccionado': usuario_id,
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

    return render(request, template, {
        'venta': venta,
        'neto': neto,
        'iva': iva,
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
    p.drawString(2 * cm, y, f"Factura de Venta #{venta.id}")
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
