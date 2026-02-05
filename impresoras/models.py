from django.db import models
from usuarios.models import Empresa


class ConfiguracionImpresoraTicket(models.Model):
    """
    Configuración de impresora térmica de tickets (ESC/POS).
    No imprime, solo define cómo debe imprimirse.
    """

    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name="config_impresora_ticket"
    )

    nombre = models.CharField(
        max_length=100,
        default="Impresora de Tickets"
    )

    # ===== IMPRESORA =====
    nombre_sistema = models.CharField(
        max_length=200,
        help_text="Nombre EXACTO de la impresora en Windows"
    )

    ancho_mm = models.PositiveIntegerField(
        default=80,
        help_text="Ancho del papel (58 u 80 mm)"
    )

    cortar_papel = models.BooleanField(
        default=True,
        help_text="Enviar comando de corte al finalizar"
    )

    abrir_cajon = models.BooleanField(
        default=False,
        help_text="Abrir cajón de dinero al imprimir"
    )

    # ===== TEXTO =====
    font_size = models.PositiveIntegerField(
        default=1,
        help_text="ESC/POS font size (1 normal)"
    )

    line_spacing = models.PositiveIntegerField(
        default=30,
        help_text="Espaciado entre líneas (ESC/POS)"
    )

    # ===== DEBUG =====
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.empresa} - {self.nombre}"
