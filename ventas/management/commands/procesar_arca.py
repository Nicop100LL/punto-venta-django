from django.core.management.base import BaseCommand
from django.utils import timezone
from ventas.models import ComprobanteArca
from ventas.arca.service import enviar_a_arca


class Command(BaseCommand):
    help = "Procesa comprobantes ARCA pendientes"

    def handle(self, *args, **kwargs):

        comprobantes = ComprobanteArca.objects.filter(
            estado__in=["pendiente", "error"],
            intentos__lt=3
        )[:20]

        if not comprobantes:
            self.stdout.write("No hay comprobantes pendientes.")
            return

        for comp in comprobantes:

            try:

                # registrar intento
                comp.intentos += 1
                comp.ultimo_intento = timezone.now()
                comp.save(update_fields=["intentos", "ultimo_intento"])

                # enviar a ARCA
                respuesta = enviar_a_arca(comp)

                comp.estado = "aprobado"
                comp.cae = respuesta["cae"]
                comp.numero = respuesta["numero"]
                comp.vencimiento_cae = respuesta["vencimiento"]
                comp.enviado_en = timezone.now()

                comp.save(update_fields=[
                    "estado",
                    "cae",
                    "numero",
                    "vencimiento_cae",
                    "enviado_en"
                ])

                self.stdout.write(
                    f"Venta {comp.venta.id} enviada a ARCA correctamente"
                )

            except Exception as e:

                comp.estado = "error"
                comp.mensaje_error = str(e)

                comp.save(update_fields=["estado", "mensaje_error"])

                self.stdout.write(
                    f"Error enviando venta {comp.venta.id}: {e}"
                )