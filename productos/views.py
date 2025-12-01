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

        aplica_descuento = 'aplica_descuento' in request.POST
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


from decimal import Decimal, InvalidOperation
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# Si ya tenés parse_decimal y querés seguir usándolo, puedes usarlo en lugar
# de Decimal(...) después de limpiar la cadena. Aquí uso Decimal directamente.

def _clean_number_string(s):
    """
    Limpia una cadena numérica en formato human-readable:
    - "1.700" -> "1700"
    - "12.450,75" -> "12450.75"
    - "4,5" -> "4.5"
    Devuelve string listo para Decimal(...) o None si s es vacío.
    """
    if s is None:
        return None
    s = str(s).strip()
    if s == '':
        return None
    # Eliminar espacios
    s = s.replace(' ', '')
    # Quitar puntos (separador de miles)
    s = s.replace('.', '')
    # Reemplazar coma decimal por punto
    s = s.replace(',', '.')
    return s

@login_required
def editar_producto(request, id):
    producto = get_object_or_404(Producto, id=id, empresa=request.user.empresa)

    if request.method == 'POST':
        producto.nombre = request.POST.get('nombre', producto.nombre)
        producto.codigo = request.POST.get('codigo', producto.codigo)
        # --- VALIDACIÓN DE CÓDIGO DUPLICADO ---
        codigo_post = request.POST.get('codigo', '').strip()
        if Producto.objects.filter(
                empresa=request.user.empresa,
                codigo=codigo_post
            ).exclude(id=producto.id).exists():
            
            messages.error(request, "Ya existe un producto con ese código.")
            categorias = Categoria.objects.filter(empresa=request.user.empresa)
            return render(request, 'productos/editar_producto.html', {
                'producto': producto,
                'categorias': categorias,
            })


        # --- PRECIOS Y STOCK: limpiamos antes de convertir ---
        raw_precio_venta = request.POST.get('precio_venta')
        raw_precio_compra = request.POST.get('precio_compra')
        raw_stock = request.POST.get('stock_actual')

        precio_venta_str = _clean_number_string(raw_precio_venta)
        precio_compra_str = _clean_number_string(raw_precio_compra)
        stock_str = _clean_number_string(raw_stock)

        try:
            if precio_venta_str is not None:
                producto.precio_venta = Decimal(precio_venta_str)
            # si no viene, mantenemos el valor anterior

            if precio_compra_str is not None:
                producto.precio_compra = Decimal(precio_compra_str)

            if stock_str is not None:
                stock_nuevo = Decimal(stock_str)
                producto.stock_actual = max(stock_nuevo, Decimal('0'))
        except (InvalidOperation, ValueError):
            messages.error(request, 'Formato de número inválido. Revisa precios y stock.')
            categorias = Categoria.objects.filter(empresa=request.user.empresa)
            return render(request, 'productos/editar_producto.html', {
                'producto': producto,
                'categorias': categorias,
            })

        categoria_id = request.POST.get('categoria')
        if categoria_id:
            producto.categoria = Categoria.objects.get(id=categoria_id, empresa=request.user.empresa)

        producto.aplica_descuento = 'aplica_descuento' in request.POST

        if producto.aplica_descuento:
            # cantidad minima y porcentaje también pueden venir formateados
            raw_cant_min = request.POST.get('cantidad_minima_descuento')
            cant_min_str = _clean_number_string(raw_cant_min)
            try:
                producto.cantidad_minima_descuento = int(Decimal(cant_min_str)) if cant_min_str is not None else 0
            except (InvalidOperation, ValueError, TypeError):
                producto.cantidad_minima_descuento = 0

            raw_porcentaje = request.POST.get('porcentaje_descuento')
            porcentaje_str = _clean_number_string(raw_porcentaje)
            try:
                producto.porcentaje_descuento = Decimal(porcentaje_str) if porcentaje_str is not None else None
            except (InvalidOperation, ValueError, TypeError):
                producto.porcentaje_descuento = None
        else:
            producto.cantidad_minima_descuento = 0
            producto.porcentaje_descuento = None

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

    # --- Formatear precio ---
    def formatear_precio(valor):
        valor_int = int(valor)
        return "${:,}".format(valor_int).replace(",", ".")

    productos = Producto.objects.filter(empresa=request.user.empresa).order_by('categoria__nombre')
    productos_por_categoria = defaultdict(list)

    for prod in productos:
        productos_por_categoria[prod.categoria.nombre].append(prod)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=\"productos.pdf\"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    # Coordenada fija para alinear precios
    X_PRECIO = 500

    # --- Título principal ---
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"📄 Lista de Productos - {request.user.empresa.nombre}")
    y -= 40

    # -----------------------------------
    # RECORRER CATEGORÍAS
    # -----------------------------------
    for categoria, productos_categoria in productos_por_categoria.items():

        # Salto de página si no hay espacio
        if y < 100:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica-Bold", 16)
            p.drawString(50, y, f"📄 Lista de Productos - {request.user.empresa.nombre}")
            y -= 40

        # Nombre categoría
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, f"▶ {categoria}")
        y -= 25

        # Encabezados de tabla
        p.setFont("Helvetica-Bold", 12)
        p.drawString(70, y, "Código")
        p.drawString(170, y, "Nombre")
        p.drawRightString(X_PRECIO, y, "Precio")  # Alineado con los valores
        y -= 20

        p.setFont("Helvetica", 10)

        # -----------------------------------
        # PRODUCTOS DENTRO DE LA CATEGORÍA
        # -----------------------------------
        for prod in productos_categoria:

            # Si no hay espacio, salto de página
            if y < 60:
                p.showPage()
                y = height - 50

                # Reimprimir encabezado de la categoría
                p.setFont("Helvetica-Bold", 14)
                p.drawString(50, y, f"▶ {categoria}")
                y -= 25

                p.setFont("Helvetica-Bold", 12)
                p.drawString(70, y, "Código")
                p.drawString(170, y, "Nombre")
                p.drawRightString(X_PRECIO, y, "Precio")
                y -= 20

                p.setFont("Helvetica", 10)

            # Datos de producto
            p.drawString(70, y, str(prod.codigo))
            p.drawString(170, y, prod.nombre)
            p.drawRightString(X_PRECIO, y, formatear_precio(prod.precio_venta))

            # Línea separadora
            p.line(50, y - 2, width - 50, y - 2)

            y -= 18

        y -= 15

    # Cerrar PDF
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
