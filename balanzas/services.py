from decimal import Decimal

from django.db import transaction

from .etiqueta import parsear_etiqueta
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
    """Si el código es una etiqueta de balanza válida y el PLU está cargado,
    devuelve (producto, importe Decimal). Si no, None."""
    if len(codigo) != 13 or not codigo.isdigit():
        return None
    for b in Balanza.objects.filter(empresa=empresa, activa=True).exclude(formato_etiqueta=''):
        r = parsear_etiqueta(b.formato_etiqueta, codigo)
        if not r:
            continue
        plu, imp = r
        pb = (ProductoBalanza.objects.filter(balanza=b, plu=plu)
              .select_related('producto').first())
        p = pb.producto if pb else None
        if p and p.activo and not p.venta_por_caja and p.empresa_id == empresa.id:
            return p, Decimal(imp).scaleb(-b.decimales_precio)
    return None
