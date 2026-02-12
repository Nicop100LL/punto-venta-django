from django.db import models
from usuarios.models import Empresa

class ConfiguracionImpresoraTicket(models.Model):
    """
    Configuración de impresora térmica de tickets (ESC/POS).
    Define cómo se debe imprimir un ticket para cada empresa.
    """

    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name="config_impresora_ticket"
    )

    nombre = models.CharField(
        max_length=100,
        default="Impresora de Tickets",
        help_text="Nombre descriptivo de la impresora"
    )

    # ===== IMPRESORA =====
    nombre_sistema = models.CharField(
        max_length=200,
        help_text="Nombre EXACTO de la impresora en Windows"
    )

    TIPO_CONEXION_CHOICES = [
        ('usb', 'USB'),
        ('lan', 'LAN')
    ]
    tipo_conexion = models.CharField(
        max_length=10,
        choices=TIPO_CONEXION_CHOICES,
        default='usb',
        help_text="Tipo de conexión de la impresora"
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
    
     # ===== PERSONALIZACIÓN =====
    logo = models.ImageField(upload_to="logos_impresora/", null=True, blank=True)
    saludo_final = models.TextField(blank=True, null=True)
    datos_empresa = models.TextField(blank=True, null=True)
    
    microservicio_url = models.URLField(
        blank=True, 
        null=True,
        help_text="URL del microservicio ESC/POS en la PC del cliente"
    )


    # ===== DEBUG / PRUEBA =====
    activo = models.BooleanField(default=True, help_text="Si está activo, se usará este microservicio")
    ultimo_test = models.DateTimeField(null=True, blank=True, help_text="Fecha del último test de impresión")
    test_ok = models.BooleanField(default=False, help_text="Resultado del último test de impresión")

    def __str__(self):
        return f"{self.empresa} - {self.nombre}"
