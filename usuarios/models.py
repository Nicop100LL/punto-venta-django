from django.contrib.auth.models import AbstractUser
from django.db import models

class Empresa(models.Model):
    nombre = models.CharField(max_length=100)
    cuit = models.CharField(max_length=13, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    condicion_iva = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)  # logo opcional
    activo = models.BooleanField(default=True)  # empresa activa o no
    
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