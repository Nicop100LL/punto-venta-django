from django.contrib.auth.models import AbstractUser
from django.db import models

FORMATO_TICKET_CHOICES = [
    ('80mm', 'Ticket 80mm (térmica)'),
    ('58mm', 'Ticket 58mm (térmica)'),
    ('a4', 'Boleta A4'),
]

class Empresa(models.Model):
    nombre = models.CharField(max_length=100)
    cuit = models.CharField(max_length=13, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    condicion_iva = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)  # logo opcional
    activo = models.BooleanField(default=True)  # empresa activa o no
    mostrar_aviso = models.BooleanField(
        default=False,
        help_text="Tildar para mostrar el mensaje de aviso a todos los usuarios."
    )
    mensaje_aviso = models.CharField(
        max_length=255,
        blank=True,
        default="💳 El pago del sistema está pendiente. Por favor regularizá.",
        help_text="Texto que se muestra en el banner de aviso."
    )
    mensaje_aviso = models.CharField(
        max_length=255,
        blank=True,
        default="💳 El pago del sistema está pendiente. Por favor regularizá.",
        verbose_name="Mensaje del aviso"
    )
    TIPO_AVISO_CHOICES = [
        ("info", "🔵 Informativo (azul)"),
        ("naranja", "🟠 Atención (naranja)"),
        ("rojo", "🔴 Urgente (rojo)"),
    ]
    tipo_aviso = models.CharField(
        max_length=10,
        choices=TIPO_AVISO_CHOICES,
        default="naranja",
        verbose_name="Color del aviso"
    )
    
    formato_ticket = models.CharField(
        max_length=10,
        choices=FORMATO_TICKET_CHOICES,
        default='80mm',
        help_text="Formato del comprobante tipo ticket para esta empresa"
    )
    
    # --- CONFIGURACIÓN ARCA ---
    usa_arca = models.BooleanField(
        default=False,
        help_text="Indica si la empresa factura con ARCA"
    )

    arca_punto_venta = models.IntegerField(
        blank=True,
        null=True
    )

    arca_certificado = models.FileField(
        upload_to="arca/",
        blank=True,
        null=True
    )

    arca_clave_privada = models.FileField(
        upload_to="arca/",
        blank=True,
        null=True
    )

    arca_modo = models.CharField(
        max_length=20,
        choices=[
            ("homologacion", "Homologación"),
            ("produccion", "Producción"),
        ],
        default="homologacion"
    )
    
    arca_alicuota_iva_default = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.5,
        help_text="Alícuota de IVA por defecto para comprobantes ARCA (ej: 10.5 o 21.0)"
    )
    
    def __str__(self):
        return self.nombre

class Usuario(AbstractUser):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True)
    es_empleado = models.BooleanField(
        default=False,
        help_text="Si está tildado, necesita abrir caja para vender y tiene restricciones de acceso"
    )

    def is_superuser_or_staff(self):
        return self.is_superuser or self.is_staff

class Cliente(models.Model):
    nombre = models.CharField(max_length=255)
    cuit = models.CharField(max_length=20, blank=True, null=True)
    condicion_iva = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.nombre