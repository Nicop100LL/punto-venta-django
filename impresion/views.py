from django.shortcuts import render, get_object_or_404
from .models import ModeloImpresion
from productos.models import Producto

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

    # 🔑 Modelo de impresión
    modelo = get_object_or_404(
        ModeloImpresion,
        id=modelo_id,
        empresa=request.user.empresa,   # 🔐 multi-empresa
        activo=True
    )

    # IDs seleccionados
    ids = [int(i) for i in productos_ids.split(",") if i.isdigit()]

    productos_qs = Producto.objects.filter(
        id__in=ids,
        empresa=request.user.empresa    # 🔐 seguridad
    )

    # mantener orden de selección
    productos = sorted(productos_qs, key=lambda p: ids.index(p.id))

    # 🧠 cálculo por hoja
    por_hoja = modelo.columnas * modelo.filas
    if por_hoja <= 0:
        return HttpResponse("Configuración inválida del modelo", status=400)

    # 📄 dividir en hojas reales
    hojas = [
        productos[i:i + por_hoja]
        for i in range(0, len(productos), por_hoja)
    ]

    return render(request, "impresion/imprimir_etiquetas.html", {
        "modelo": modelo,
        "hojas": hojas,
    })