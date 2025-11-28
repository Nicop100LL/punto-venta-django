from collections import defaultdict
from decimal import Decimal, InvalidOperation
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from .models import Producto, Categoria


def parse_decimal(value):
    """
    Convierte una cadena a Decimal, reemplazando comas por puntos y eliminando comillas raras.
    Si viene vacía o inválida, devuelve 0.
    """
    if not value:
        return Decimal('0')
    value = str(value).replace(',', '.').replace('“', '').replace('”', '').strip()
    try:
        return Decimal(value)
    except InvalidOperation:
        return Decimal('0')


@login_required
def lista_productos(request):
    productos = Producto.objects.filter(empresa=request.user.empresa)
    categorias = Categoria.objects.filter(empresa=request.user.empresa)
    return render(request, 'productos/lista_productos.html', {
        'productos': productos,
        'categorias': categorias,
    })


@login_required
def nuevo_producto(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With', '').lower() == 'xmlhttprequest':
        nombre = request.POST.get('nombre')
        codigo = request.POST.get('codigo')
        categoria_id = request.POST.get('categoria')
        tipo_venta = request.POST.get('tipo_venta')

        precio_venta = parse_decimal(request.POST.get('precio_venta'))
        precio_compra = parse_decimal(request.POST.get('precio_compra', 0))
        stock_actual = parse_decimal(request.POST.get('stock_actual'))

        aplica_descuento = request.POST.get('aplica_descuento') == 'True'
        if aplica_descuento:
            cantidad_minima_descuento = request.POST.get('cantidad_minima_descuento')
            porcentaje_descuento = parse_decimal(request.POST.get('porcentaje_descuento'))
        else:
            cantidad_minima_descuento = None
            porcentaje_descuento = None

        if Producto.objects.filter(codigo=codigo, empresa=request.user.empresa).exists():
            return JsonResponse({'success': False, 'message': 'El código de producto ya existe para esta empresa.'})

        categoria = get_object_or_404(Categoria, id=categoria_id, empresa=request.user.empresa)

        producto = Producto.objects.create(
            nombre=nombre,
            codigo=codigo,
            categoria=categoria,
            precio_venta=precio_venta,
            precio_compra=precio_compra,
            stock_actual=stock_actual,
            empresa=request.user.empresa,
            tipo_venta=tipo_venta,
            aplica_descuento=aplica_descuento,
            cantidad_minima_descuento=int(cantidad_minima_descuento) if cantidad_minima_descuento else 0,
            porcentaje_descuento=porcentaje_descuento,
        )

        return JsonResponse({
            'success': True,
            'producto': {
                'id': producto.id,
                'nombre': producto.nombre,
                'codigo': producto.codigo,
                'categoria': producto.categoria.nombre,
                'categoria_id': producto.categoria.id,
                'precio_venta': float(producto.precio_venta),
                'stock_actual': float(producto.stock_actual),
                'tipo_venta': producto.tipo_venta,
            }
        })

    return JsonResponse({'success': False, 'message': 'Método no permitido o no es una solicitud AJAX.'})


@login_required
def editar_producto(request, id):
    producto = get_object_or_404(Producto, id=id, empresa=request.user.empresa)

    if request.method == 'POST':
        producto.nombre = request.POST.get('nombre', producto.nombre)
        producto.codigo = request.POST.get('codigo', producto.codigo)

        producto.precio_venta = parse_decimal(request.POST.get('precio_venta'))
        producto.precio_compra = parse_decimal(request.POST.get('precio_compra'))
        stock_nuevo = parse_decimal(request.POST.get('stock_actual'))
        producto.stock_actual = max(stock_nuevo, Decimal('0'))  # Evitar negativo

        categoria_id = request.POST.get('categoria')
        if categoria_id:
            producto.categoria = Categoria.objects.get(id=categoria_id)

        producto.aplica_descuento = request.POST.get('aplica_descuento') == 'True'
        cantidad_minima_descuento = request.POST.get('cantidad_minima_descuento')
        producto.cantidad_minima_descuento = int(cantidad_minima_descuento) if cantidad_minima_descuento else 0
        producto.porcentaje_descuento = parse_decimal(request.POST.get('porcentaje_descuento'))

        producto.save()
        messages.success(request, 'Producto actualizado correctamente.')
        return redirect('lista_productos')

    categorias = Categoria.objects.filter(empresa=request.user.empresa)
    return render(request, 'productos/editar_producto.html', {
        'producto': producto,
        'categorias': categorias,
    })


@login_required
def eliminar_producto(request, id):
    producto = get_object_or_404(Producto, id=id, empresa=request.user.empresa)
    producto.delete()
    messages.success(request, 'Producto eliminado correctamente.')
    return redirect('lista_productos')


@login_required
def exportar_productos_pdf(request):
    productos = Producto.objects.filter(empresa=request.user.empresa).order_by('categoria__nombre')
    productos_por_categoria = defaultdict(list)
    for prod in productos:
        productos_por_categoria[prod.categoria.nombre].append(prod)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="productos.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"Lista de Productos - {request.user.empresa.nombre}")
    y -= 40

    for categoria, productos_categoria in productos_por_categoria.items():
        if y < 80:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica-Bold", 16)
            p.drawString(50, y, f"Lista de Productos - {request.user.empresa.nombre}")
            y -= 40

        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, categoria)
        y -= 25

        p.setFont("Helvetica-Bold", 12)
        p.drawString(70, y, "Código")
        p.drawString(170, y, "Nombre")
        p.drawString(400, y, "Precio")
        y -= 20

        p.setFont("Helvetica", 10)
        for prod in productos_categoria:
            if y < 50:
                p.showPage()
                y = height - 50
                p.setFont("Helvetica-Bold", 14)
                p.drawString(50, y, categoria)
                y -= 25
                p.setFont("Helvetica-Bold", 12)
                p.drawString(70, y, "Código")
                p.drawString(170, y, "Nombre")
                p.drawString(400, y, "Precio")
                y -= 20
                p.setFont("Helvetica", 10)

            p.drawString(70, y, str(prod.codigo))
            p.drawString(170, y, prod.nombre)
            p.drawString(400, y, f"${prod.precio_venta}")
            p.line(50, y - 2, width - 50, y - 2)
            y -= 18

        y -= 15

    p.showPage()
    p.save()
    return response


@login_required
@require_POST
def nueva_categoria(request):
    nombre = request.POST.get('nombre')
    empresa = request.user.empresa
    if Categoria.objects.filter(nombre__iexact=nombre, empresa=empresa).exists():
        return JsonResponse({'success': False, 'message': 'La categoría ya existe.'})

    cat = Categoria.objects.create(nombre=nombre, empresa=empresa)
    return JsonResponse({'success': True, 'id': cat.id, 'nombre': cat.nombre})


@login_required
def buscar_producto_por_codigo(request):
    codigo = request.GET.get('codigo')
    empresa = request.user.empresa
    try:
        producto = Producto.objects.get(codigo=codigo, empresa=empresa)
        return JsonResponse({
            'success': True,
            'nombre': producto.nombre,
            'precio_venta': float(producto.precio_venta),
            'stock_actual': float(producto.stock_actual),
            'tipo_venta': producto.tipo_venta,
            'codigo': producto.codigo,
        })
    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Producto no encontrado'})
