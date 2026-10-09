from decimal import Decimal

from django.db import transaction

from .etiqueta import parsear_peso
from .models import Balanza, CambioBalanza, ProductoBalanza


def tipo_venta_balanza(producto):
    return 'P' if producto.tipo_venta == 'kilo' else 'U'


def registrar_cambio(pb, tipo, producto=None):
    """Encola un cambio; si ya hay uno pendiente para ese PLU, lo actualiza."""
    p = producto or pb.producto
    datos = dict(nombre=p.nombre, precio=p.precio_venta, tipo_venta=tipo_venta_balanza(p))
    with transaction.atomic():
        pend = (CambioBalanza.objects.select_for_update()
                .filter(balanza=pb.balanza, plu=pb.plu, estado='pendiente').first())
        if not pend:
            return CambioBalanza.objects.create(balanza=pb.balanza, plu=pb.plu, tipo=tipo, **datos)
        if tipo == 'baja':
            nuevo = 'baja'
        elif pend.tipo == 'baja' or 'alta' in (pend.tipo, tipo):
            nuevo = 'alta'
        else:
            nuevo = 'precio'
        pend.tipo = nuevo
        for k, v in datos.items():
            setattr(pend, k, v)
        pend.version += 1
        pend.intentos = 0
        pend.error_detalle = ''
        pend.save()
        return pend


def buscar_por_etiqueta(empresa, codigo):
    """Devuelve (producto, peso_kg) para una etiqueta de balanza."""

    if len(codigo) != 13 or not codigo.isdigit():
        return None

    for b in Balanza.objects.filter(
        empresa=empresa,
        activa=True
    ).exclude(formato_etiqueta=''):

        resultado = parsear_peso(b.formato_etiqueta, codigo)
        if not resultado:
            continue

        plu, peso_gramos = resultado

        pb = (
            ProductoBalanza.objects
            .filter(balanza=b, plu=plu)
            .select_related('producto')
            .first()
        )

        producto = pb.producto if pb else None

        if (
            producto
            and producto.activo
            and not producto.venta_por_caja
            and producto.empresa_id == empresa.id
        ):
            peso_kg = Decimal(peso_gramos) / Decimal('1000')
            return producto, peso_kg

    return None