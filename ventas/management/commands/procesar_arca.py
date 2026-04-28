from django.core.management.base import BaseCommand
from django.utils import timezone
from ventas.models import ComprobanteArca
from ventas.services.arca import enviar_a_arca
from datetime import datetime

class Command(BaseCommand):
    help = "Procesa comprobantes ARCA pendientes"

    ERRORES_FATALES = [
        "token",
        "sign",
        "autenticacion",
        "CEE ya posee un TA",
    ]

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
                comp.intentos += 1
                comp.ultimo_intento = timezone.now()
                comp.save(update_fields=["intentos", "ultimo_intento"])

                respuesta = enviar_a_arca(comp)

                comp.estado = "aprobado"
                comp.cae = respuesta["cae"]
                comp.numero = respuesta["numero"]
                
                venc = respuesta["vencimiento"]
                comp.vencimiento_cae = datetime.strptime(venc, "%Y%m%d").date()
                comp.enviado_en = timezone.now()
                comp.save(update_fields=[
                    "estado", "cae", "numero", "vencimiento_cae", "enviado_en"
                ])

                self.stdout.write(
                    f"✅ Venta {comp.venta.id} enviada a ARCA correctamente"
                )

            except Exception as e:
                error_str = str(e).lower()

                comp.estado = "error"
                comp.mensaje_error = str(e)
                comp.save(update_fields=["estado", "mensaje_error"])

                self.stdout.write(
                    f"❌ Error enviando venta {comp.venta.id}: {e}"
                )

                # Si es un error de autenticación cortamos todo
                # No tiene sentido seguir si el token no sirve
                if any(fatal.lower() in error_str for fatal in self.ERRORES_FATALES):
                    self.stdout.write(
                        "⚠️  Error fatal de autenticación, interrumpiendo proceso."
                    )
                    break