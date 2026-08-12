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

    alerta_stock_bajo = models.BooleanField(default=False)
    stock_minimo_alerta = models.PositiveIntegerField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    dias_aviso_vencimiento = models.PositiveIntegerField(null=True, blank=True, default=7)
    
    # ===== VENTA POR BULTO (opcional) =====
    vende_por_bulto = models.BooleanField(default=False)
    unidades_por_bulto = models.PositiveIntegerField(null=True, blank=True)
    precio_por_bulto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_descuento_manual = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        unique_together = ('codigo', 'empresa')
        
    def clean(self):
        # Evita stock negativo
        if self.stock_actual < 0:
            self.stock_actual = 0 # Forzamos a cero

        if self.vende_por_bulto and (not self.unidades_por_bulto or not self.precio_por_bulto):
            raise ValidationError("Si vende por bulto, indicá las unidades y el precio del bulto.")    

    def save(self, *args, **kwargs):
        self.full_clean()  # Llama a clean antes de guardar
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"
    
    def precio_con_descuento(self):
        if self.aplica_descuento and self.porcentaje_descuento:
            descuento = self.precio_venta * (self.porcentaje_descuento / 100)
            return self.precio_venta - descuento
        return None
    
    def precio_unitario_bulto(self):
        if self.vende_por_bulto and self.unidades_por_bulto and self.precio_por_bulto:
            return self.precio_por_bulto / self.unidades_por_bulto
        return None
    
    
class ControlAvisoVencimiento(models.Model):
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE)
    ultimo_aviso = models.DateTimeField(null=True, blank=True)