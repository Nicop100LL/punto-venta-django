import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from productos.models import Producto

from .models import ProductoBalanza
from .services import registrar_cambio

logger = logging.getLogger(__name__)
CAMPOS = ('precio_venta', 'nombre', 'activo', 'tipo_venta', 'venta_por_caja')


@receiver(pre_save, sender=Producto, dispatch_uid='balanzas_pre_save_producto')
def _guardar_previo(sender, instance, raw=False, **kwargs):
    instance._balanza_previo = None
    if raw or not instance.pk:
        return
    try:
        # Consulta liviana: solo sigue si el producto está en alguna balanza
        if ProductoBalanza.objects.filter(producto_id=instance.pk).exists():
            instance._balanza_previo = (Producto.objects.filter(pk=instance.pk)
                                        .values(*CAMPOS).first())
    except Exception:
        logger.exception('balanzas: error leyendo estado previo')


@receiver(post_save, sender=Producto, dispatch_uid='balanzas_post_save_producto')
def _encolar_cambio(sender, instance, created, raw=False, **kwargs):
    previo = getattr(instance, '_balanza_previo', None)
    if raw or created or not previo:
        return
    try:
        ahora = {c: getattr(instance, c) for c in CAMPOS}
        if ahora == previo:
            return
        estaba = previo['activo'] and not previo['venta_por_caja']
        sale = (not ahora['activo']) or ahora['venta_por_caja']
        if sale:
            if not estaba:
                return
            tipo = 'baja'
        elif (not estaba or previo['nombre'] != ahora['nombre']
              or previo['tipo_venta'] != ahora['tipo_venta']):
            tipo = 'alta'
        else:
            tipo = 'precio'
        for pb in (ProductoBalanza.objects.filter(producto=instance, balanza__activa=True)
                   .select_related('balanza')):
            registrar_cambio(pb, tipo, producto=instance)
    except Exception:
        # Nunca debe impedir guardar un producto
        logger.exception('balanzas: error encolando cambio de producto %s', instance.pk)
