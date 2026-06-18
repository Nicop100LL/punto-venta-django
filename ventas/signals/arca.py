# ventas/signals/arca.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from ventas.models import Venta, ComprobanteArca
from ventas.arca.service import decidir_arca
from usuarios.models import Empresa
from ventas.models import ReglaArcaPago


@receiver(post_save, sender=Venta)
def crear_comprobante_automatico(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.total < 0:
        return
    if not instance.empresa.arca_punto_venta:  
        return

    decision = decidir_arca(instance)

    if (
        decision.get("subir_a_arca")
        and decision.get("tipo")
        and not hasattr(instance, "comprobante_arca")
    ):
        ComprobanteArca.objects.create(
            venta=instance,
            tipo=decision["tipo"],
            estado="pendiente",
            alicuota_iva=instance.empresa.arca_alicuota_iva_default,
        )


@receiver(post_save, sender=Empresa)
def crear_reglas_arca(sender, instance, created, **kwargs):
    if not created:
        return

    reglas = [
        ("EF", False),
        ("TR", True),
        ("TJ", True),
        ("MP", True),
        ("DN", True),
    ]

    for tipo, subir in reglas:
        ReglaArcaPago.objects.create(
            empresa=instance,
            tipo_pago=tipo,
            subir_a_arca=subir,
            tipo_comprobante="cf"
        )