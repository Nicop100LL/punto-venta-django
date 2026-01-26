from django.shortcuts import render, get_object_or_404
from .models import ModeloImpresion
from productos.models import Producto
from .barcodes import code128_svg_base64
from django.contrib.auth.decorators import login_required

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
