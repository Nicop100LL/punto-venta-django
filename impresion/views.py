from django.shortcuts import render, get_object_or_404
from .models import ModeloImpresion
from productos.models import Producto
from .barcodes import code128_svg_base64
from django.contrib.auth.decorators import login_required



from .models import ModeloEtiqueta

from django.http import HttpResponse

@login_required
def configurar_impresion(request):
    empresa = request.user.empresa  # o como la obtengas
    modelos = ModeloImpresion.objects.filter(empresa=empresa, activo=True)

    productos = Producto.objects.filter(empresa=empresa)

    return render(request, "impresion/configurar.html", {
        "modelos": modelos,
        "productos": productos,
    })



@login_required
def imprimir_etiquetas(request):
    modelo_id = request.GET.get("modelo")
    productos_ids = request.GET.get("productos")

    if not modelo_id or not productos_ids:
        return HttpResponse("Datos incompletos", status=400)

    modelo = get_object_or_404(
        ModeloImpresion,
        id=modelo_id,
        empresa=request.user.empresa,
        activo=True
    )

    ids = [int(i) for i in productos_ids.split(",") if i.isdigit()]

    productos_qs = Producto.objects.filter(
        id__in=ids,
        empresa=request.user.empresa
    )

    productos = sorted(productos_qs, key=lambda p: ids.index(p.id))

    # 👉 generar barcode solo si el modelo lo usa
    if modelo.mostrar_barcode:
        for producto in productos:
            producto.barcode_svg = code128_svg_base64(producto.codigo)

    por_hoja = modelo.columnas * modelo.filas
    hojas = [
        productos[i:i + por_hoja]
        for i in range(0, len(productos), por_hoja)
    ]

    return render(request, "impresion/imprimir_etiquetas.html", {
        "modelo": modelo,
        "hojas": hojas,
    })

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from productos.models import Producto
from .models import ModeloEtiqueta
from .barcodes import code128_svg_base64  # asumimos que ya tienes esta función
from django.http import HttpResponse

@login_required
def imprimir_etiquetas_prueba(request):
    """
    Genera un PDF o vista HTML de prueba para etiquetas de productos.
    No imprime, solo muestra cómo quedaría la etiqueta.
    """
    modelo_id = request.GET.get("modelo")
    productos_ids = request.GET.get("productos")

    if not modelo_id or not productos_ids:
        return HttpResponse("Datos incompletos", status=400)

    modelo = get_object_or_404(
        ModeloEtiqueta,
        id=modelo_id,
        empresa=request.user.empresa,
        activo=True
    )

    ids = [int(i) for i in productos_ids.split(",") if i.isdigit()]
    productos_qs = Producto.objects.filter(
        id__in=ids,
        empresa=request.user.empresa
    )
    # Mantener el orden
    productos = sorted(productos_qs, key=lambda p: ids.index(p.id))

    # Generar barcode si corresponde
    if modelo.mostrar_barcode:
        for producto in productos:
            producto.barcode_svg = code128_svg_base64(producto.codigo)

    # Renderizamos HTML de prueba para cada producto como etiqueta
    return render(request, "impresion/prueba_etiquetas.html", {
        "modelo": modelo,
        "productos": productos,
    })



from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.units import mm
from productos.models import Producto
from .models import ModeloEtiqueta

def draw_centered(c, text, y, ancho, font_name, font_size):
    c.setFont(font_name, font_size)
    c.drawCentredString(ancho/2, y, text)

@login_required
def imprimir_etiquetas_pdf(request):
    modelo_id = request.GET.get("modelo")
    productos_ids = request.GET.get("productos")

    if not modelo_id or not productos_ids:
        return HttpResponse("Datos incompletos", status=400)

    modelo = get_object_or_404(
        ModeloEtiqueta,
        id=modelo_id,
        empresa=request.user.empresa,
        activo=True
    )

    # Parsear productos y cantidad
    productos_param = productos_ids.split(",")
    productos = []

    for par in productos_param:
        if ":" in par:
            pid, qty = par.split(":")
            if pid.isdigit() and qty.isdigit():
                producto = get_object_or_404(
                    Producto,
                    id=int(pid),
                    empresa=request.user.empresa
                )
                for _ in range(int(qty)):
                    productos.append(producto)
        elif par.isdigit():
            producto = get_object_or_404(
                Producto,
                id=int(par),
                empresa=request.user.empresa
            )
            productos.append(producto)

    # Preparar PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="etiquetas.pdf"'

    ancho = modelo.ancho_mm * mm
    alto = modelo.alto_mm * mm
    c = canvas.Canvas(response, pagesize=(ancho, alto))

    PT_PER_MM = 2.83464567  # Puntos por mm

    for producto in productos:
        y = alto - modelo.margen_superior * mm

        # ===== NOMBRE =====
        if modelo.mostrar_nombre:
            draw_centered(
                c,
                producto.nombre,
                y,
                ancho,
                "Helvetica-Bold" if modelo.nombre_negrita else "Helvetica",
                modelo.nombre_tamano
            )
            y -= (modelo.nombre_tamano + 2) * mm / PT_PER_MM  # convertir px a mm aprox

        # ===== PRECIO =====
        if modelo.mostrar_precio:
            draw_centered(
                c,
                f"$ {producto.precio_venta}",
                y,
                ancho,
                "Helvetica-Bold" if modelo.precio_negrita else "Helvetica",
                modelo.precio_tamano
            )
            y -= (modelo.precio_tamano + 2) * mm / PT_PER_MM

        # ===== CODIGO DE BARRAS =====
       
        if modelo.mostrar_barcode:
            barcode_height_pt = modelo.barcode_alto * PT_PER_MM  # mm → pt
            barcode = code128.Code128(
                producto.codigo,
                barHeight=barcode_height_pt,
                barWidth=0.6
            )

            # Escalar horizontalmente para que encaje en ancho definido
            scale_x = (modelo.barcode_ancho * mm) / barcode.width
            c.saveState()
            c.translate((ancho - barcode.width * scale_x)/2, y - barcode_height_pt)
            c.scale(scale_x, 1)  # solo escala horizontal
            barcode.drawOn(c, 0, 0)
            c.restoreState()

            # ===== Actualizar y para el texto debajo =====
            y -= modelo.barcode_alto * mm  # mover y hacia abajo según alto real del barcode en mm
            y -= 4*mm  # un pequeño padding entre barcode y texto

            # Mostrar texto debajo del barcode si corresponde
            if modelo.barcode_mostrar_texto:
                draw_centered(
                    c,
                    producto.codigo,
                    y,
                    ancho,
                    "Helvetica",
                    8
                )
                y -= 10  # separación extra para que no se encime con lo siguiente

        # ===== BORDE DEBUG OPCIONAL =====
        # c.rect(0, 0, ancho, alto)

        c.showPage()

    c.save()
    return response
