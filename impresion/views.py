from django.shortcuts import render, get_object_or_404
from .models import ModeloImpresion
from productos.models import Producto
from .barcodes import code128_svg_base64
from django.contrib.auth.decorators import login_required
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle



from .models import ModeloEtiqueta

from django.http import HttpResponse

@login_required
def configurar_impresion(request):
    empresa = request.user.empresa  # o como la obtengas
    
    # Modelos de hoja (A4 / A5)
    modelos_hoja = ModeloImpresion.objects.filter(empresa=empresa, activo=True)
    
    # Modelos de etiqueta (58mm / 80mm)
    modelos_etiqueta = ModeloEtiqueta.objects.filter(empresa=empresa, activo=True)
    
    productos = Producto.objects.filter(empresa=empresa)

    return render(request, "impresion/configurar.html", {
        "modelos_hoja": modelos_hoja,
        "modelos_etiqueta": modelos_etiqueta,
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
    
def calcular_alto_etiqueta_mm(modelo, producto):
    alto_pt = 0

    # Márgenes (mm → pt)
    alto_pt += modelo.margen_superior * mm
    alto_pt += modelo.margen_inferior * mm

    ancho_util = (
        modelo.ancho_mm
        - modelo.margen_izquierdo
        - modelo.margen_derecho
    ) * mm

    # Nombre (multilínea real)
    if modelo.mostrar_nombre:
        h_nombre = medir_paragraph(
            producto.nombre,
            ancho_util,
            modelo.nombre_tamano,
            bold=modelo.nombre_negrita
        )
        alto_pt += h_nombre + 2 * mm

    # Precio (línea simple)
    if modelo.mostrar_precio:
        alto_pt += modelo.precio_tamano * 1.4

    # Barcode
    if modelo.mostrar_barcode:
        alto_pt += modelo.barcode_alto * 0.264 * mm
        if modelo.barcode_mostrar_texto:
            alto_pt += 4 * mm

    # Padding
    alto_pt += modelo.padding * 2 * 0.264 * mm

    # Seguridad mínima
    alto_pt = max(alto_pt, 20 * mm)

    # Convertimos a mm para coherencia
    return alto_pt / mm
def draw_paragraph_centered(c, text, x, y, width, font_size, bold=False):
    styles = getSampleStyleSheet()
    
    style = ParagraphStyle(
        name="Etiqueta",
        parent=styles["Normal"],
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=font_size,
        leading=font_size * 1.2,
        alignment=1,  # center
        spaceAfter=0,
        spaceBefore=0,
    )

    p = Paragraph(text, style)
    w, h = p.wrap(width, 1000)  # 1000 = alto máximo ficticio
    p.drawOn(c, x, y - h)

    return h  # 🔥 devolvemos la altura real


def medir_paragraph(text, width, font_size, bold=False):
    styles = getSampleStyleSheet()

    style = ParagraphStyle(
        name="Medicion",
        parent=styles["Normal"],
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=font_size,
        leading=font_size * 1.2,
        alignment=1,
    )

    p = Paragraph(text, style)
    _, h = p.wrap(width, 10_000)
    return h  # POINTS
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
    PT_PER_MM = 2.83464567  # Puntos por mm

    c = canvas.Canvas(response)

    for producto in productos:
        if modelo.alto_mm > 0:
            alto_mm = modelo.alto_mm
        else:
            alto_mm = 44

        ancho = modelo.ancho_mm * mm
        alto = alto_mm * mm

        c.setPageSize((ancho, alto))

        # y arranca desde arriba menos margen
        y = alto - modelo.margen_superior * mm

        # ancho útil con márgenes izquierdo y derecho
        ancho_util = ancho - (modelo.margen_izquierdo + modelo.margen_derecho) * mm
        x_izq = modelo.margen_izquierdo * mm

        # ===== NOMBRE =====
        if modelo.mostrar_nombre:
            h_nombre = draw_paragraph_centered(
                c,
                producto.nombre,
                x_izq,
                y,
                ancho_util,
                modelo.nombre_tamano,
                bold=modelo.nombre_negrita
            )
            y -= h_nombre + 2 * mm

        # ===== PRECIO =====
        if modelo.mostrar_precio:
            font_name = "Helvetica-Bold" if modelo.precio_negrita else "Helvetica"
            precio_texto = f"${producto.precio_venta:,.0f}".replace(",", ".")
            
            font_size = modelo.precio_tamano
            c.setFont(font_name, font_size)
            while c.stringWidth(precio_texto, font_name, font_size) > ancho_util and font_size > 6:
                font_size -= 1
                c.setFont(font_name, font_size)

            y -= font_size
            c.drawCentredString(ancho / 2, y, precio_texto)
            y -= 2 * mm

        # ===== BARCODE =====
        if modelo.mostrar_barcode:
            barcode_height_pt = modelo.barcode_alto * mm / 25.4 * 72
            barcode = code128.Code128(
                producto.codigo,
                barHeight=barcode_height_pt,
                barWidth=0.6
            )
            scale_x = (modelo.barcode_ancho * mm) / barcode.width
            c.saveState()
            c.translate((ancho - barcode.width * scale_x) / 2, y - barcode_height_pt)
            c.scale(scale_x, 1)
            barcode.drawOn(c, 0, 0)
            c.restoreState()
            y -= barcode_height_pt + 2 * mm

            if modelo.barcode_mostrar_texto:
                draw_centered(c, producto.codigo, y, ancho, "Helvetica", 8)
                y -= 10

        c.showPage()

    c.save()
    return response