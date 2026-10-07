import hashlib
import secrets

from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

from productos.models import Producto
from usuarios.models import Empresa


class AgenteBalanza(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100, default='Agente local')
    token_hash = models.CharField(max_length=64, unique=True)
    activo = models.BooleanField(default=True)
    ultimo_latido = models.DateTimeField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    is_authenticated = True  # para DRF (request.user es el agente)

    def __str__(self):
        return f'{self.nombre} ({self.empresa})'

    @staticmethod
    def hashear(token):
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def crear_con_token(cls, empresa, nombre):
        token = secrets.token_urlsafe(32)
        agente = cls.objects.create(empresa=empresa, nombre=nombre,
                                    token_hash=cls.hashear(token))
        return agente, token  # el token en claro solo se muestra una vez

    @property
    def conectado(self):
        return bool(self.ultimo_latido and
                    (timezone.now() - self.ultimo_latido).total_seconds() < 180)


class Balanza(models.Model):
    TIPOS = [('red', 'Red (WiFi/Ethernet, TCP)'), ('usb', 'USB (puerto COM)')]
    DECIMALES = [(0, 'Sin decimales'), (2, '2 decimales')]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    agente = models.ForeignKey(AgenteBalanza, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name='balanzas')
    nombre = models.CharField(max_length=100)
    direccion_equipo = models.PositiveSmallIntegerField(
        default=1, validators=[MaxValueValidator(99)],
        help_text='Número de equipo (0-99). NO es una IP.')
    tipo_conexion = models.CharField(max_length=5, choices=TIPOS, default='red')
    ip = models.GenericIPAddressField(null=True, blank=True)
    puerto = models.PositiveIntegerField(default=10001)
    puerto_com = models.CharField(max_length=20, blank=True, help_text='Ej: COM3 o /dev/ttyUSB0')
    decimales_precio = models.PositiveSmallIntegerField(choices=DECIMALES, default=0)
    sector_por_defecto = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(99)])
    formato_etiqueta = models.CharField(
        max_length=12, default='20PPPPIIIIII',
        validators=[RegexValidator(r'^[0-9PIBCSA]{12}$',
                                   'Deben ser 12 caracteres: dígitos fijos y letras P, I, B, C, S, A.')],
        help_text='Código de barras de la etiqueta/ticket (12 caracteres, sin dígito verificador). '
                  'P = PLU, I = importe. Debe coincidir con lo configurado en la balanza. '
                  'Ej: 20PPPPIIIIII')
    activa = models.BooleanField(default=True)
    ultima_comunicacion = models.DateTimeField(null=True, blank=True)
    ultimo_estado = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return self.nombre


class ProductoBalanza(models.Model):
    balanza = models.ForeignKey(Balanza, on_delete=models.CASCADE, related_name='productos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='en_balanzas')
    plu = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(999999)])

    class Meta:
        unique_together = [('balanza', 'producto'), ('balanza', 'plu')]

    def __str__(self):
        return f'PLU {self.plu} - {self.producto}'


class CambioBalanza(models.Model):
    TIPOS = [('alta', 'Alta/modificación completa'), ('precio', 'Cambio de precio'),
             ('baja', 'Baja')]
    ESTADOS = [('pendiente', 'Pendiente'), ('enviado', 'Enviado'), ('error', 'Error')]

    balanza = models.ForeignKey(Balanza, on_delete=models.CASCADE, related_name='cambios')
    plu = models.PositiveIntegerField()
    tipo = models.CharField(max_length=10, choices=TIPOS)
    nombre = models.CharField(max_length=100, blank=True)
    precio = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    tipo_venta = models.CharField(max_length=1, default='U')  # P pesable / U unitario
    estado = models.CharField(max_length=10, choices=ESTADOS, default='pendiente')
    version = models.PositiveIntegerField(default=1)  # evita perder cambios mientras se envía
    intentos = models.PositiveSmallIntegerField(default=0)
    error_detalle = models.CharField(max_length=255, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    sincronizado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['id']
        indexes = [models.Index(fields=['balanza', 'estado'])]
