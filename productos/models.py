from django.db import models
from usuarios.models import Empresa
from django.core.exceptions import ValidationError

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    TIPO_VENTA_CHOICES = [
        ('unidad', 'Unidad'),
        ('kilo', 'Kilo'),
    ]

    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=50)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=3)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    stock_actual = models.DecimalField(max_digits=10, decimal_places=3)
    tipo_venta = models.CharField(max_length=10, choices=TIPO_VENTA_CHOICES, default='unidad')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    # Nuevos campos para descuento por cantidad
    aplica_descuento = models.BooleanField(default=False)
    cantidad_minima_descuento = models.PositiveIntegerField(null=True, blank=True)
    porcentaje_descuento = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('codigo', 'empresa')



    def clean(self):
        # Evita stock negativo
        if self.stock_actual < 0:
            self.stock_actual = 0  # Forzamos a cero

    def save(self, *args, **kwargs):
        self.full_clean()  # Llama a clean antes de guardar
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"