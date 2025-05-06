from collections import defaultdict
from decimal import Decimal
from django.shortcuts import get_object_or_404, render, redirect
from productos.models import Producto, Categoria
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import JsonResponse
from .models import Categoria
from django.db import IntegrityError
from .models import Categoria
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

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
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        nombre = request.POST.get('nombre')
        codigo = request.POST.get('codigo')
        categoria_id = request.POST.get('categoria')
        precio_venta = request.POST.get('precio_venta')
        precio_compra = request.POST.get('precio_compra', None)
        stock_actual = Decimal(request.POST['stock_actual'])
        tipo_venta = request.POST.get('tipo_venta')


        # Verifica si el código ya existe para la misma empresa
        if Producto.objects.filter(codigo=codigo, empresa=request.user.empresa).exists():
            return JsonResponse({'success': False, 'message': 'El código de producto ya existe para esta empresa.'})

        # Crear producto
        categoria = get_object_or_404(Categoria, id=categoria_id, empresa=request.user.empresa)
        producto = Producto.objects.create(
            nombre=nombre,
            codigo=codigo,
            categoria=categoria,
            precio_venta=precio_venta,
            precio_compra=precio_compra,
            stock_actual=stock_actual,
            empresa=request.user.empresa,  # ¡Muy importante!
            tipo_venta=tipo_venta 
        )

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Método no permitido o no es una solicitud AJAX.'})

@login_required
def editar_producto(request, id):
    producto = get_object_or_404(Producto, id=id, empresa=request.user.empresa)
    if request.method == 'POST':
        # Actualizamos los campos del producto
        producto.nombre = request.POST.get('nombre')
        producto.codigo = request.POST.get('codigo')
        producto.precio_venta = request.POST.get('precio_venta')
        producto.stock_actual = request.POST.get('stock_actual')
        producto.precio_compra = request.POST.get('precio_compra')  # Si es obligatorio
        categoria_id = request.POST.get('categoria')
        producto.categoria = Categoria.objects.get(id=categoria_id)
        
        producto.save()  # Guardamos el producto actualizado
        messages.success(request, 'Producto actualizado correctamente.')
        return redirect('lista_productos')  # Redirigimos a la lista de productos

    # En caso de que sea un GET, pre-cargamos el producto y las categorías
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

    # Agrupar productos por categoría
    productos_por_categoria = defaultdict(list)
    for prod in productos:
        productos_por_categoria[prod.categoria.nombre].append(prod)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="productos.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    # Título principal
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"Lista de Productos - {request.user.empresa.nombre}")
    y -= 40

    for categoria, productos_categoria in productos_por_categoria.items():
        # Comprobar si hay espacio suficiente
        if y < 80:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica-Bold", 16)
            p.drawString(50, y, f"Lista de Productos - {request.user.empresa.nombre}")
            y -= 40

        # Mostrar el nombre de la categoría en negrita (sin "Categoría:")
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, categoria)
        y -= 25

        # Encabezados
        p.setFont("Helvetica-Bold", 12)
        p.drawString(70, y, "Código")
        p.drawString(170, y, "Nombre")
        p.drawString(400, y, "Precio")
        y -= 20

        # Listar productos de la categoría
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
            # Línea horizontal bajo el producto
            p.line(50, y - 2, width - 50, y - 2)
            y -= 18

        y -= 15  # Espacio entre categorías

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
            'precio_venta': float(producto.precio_venta),  # Convertido para evitar error de JSON
            'stock_actual': float(producto.stock_actual),
            'tipo_venta': producto.tipo_venta,
            'codigo': producto.codigo,
        })
    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Producto no encontrado'})