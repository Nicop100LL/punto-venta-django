from datetime import timedelta
from django.db import models
from django.utils import timezone
from productos.models import Producto
from usuarios.models import Usuario, Empresa


class Presupuesto(models.Model):
    ESTADOS = [('vigente', 'Vigente'), ('anulado', 'Anulado')]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    cliente = models.ForeignKey('ventas.Cliente', on_delete=models.SET_NULL, null=True, blank=True)
    cliente_nombre = models.CharField(max_length=100, blank=True, help_text="Para clientes no registrados")
    fecha = models.DateTimeField(default=timezone.now)
    numero_empresa = models.PositiveIntegerField(default=1)
    validez_dias = models.PositiveIntegerField(default=7)
    nota = models.TextField(blank=True, default='')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='vigente')

    class Meta:
        ordering = ['-fecha']
        unique_together = ('empresa', 'numero_empresa')

    @property
    def fecha_vencimiento(self):
        return self.fecha + timedelta(days=self.validez_dias)

    @property
    def vencido(self):
        return timezone.now() > self.fecha_vencimiento

    @property
    def nombre_cliente(self):
        if self.cliente:
            return self.cliente.nombre
        return self.cliente_nombre or 'Consumidor Final'

    def __str__(self):
        return f"Presupuesto #{self.numero_empresa}"


class DetallePresupuesto(models.Model):
    presupuesto = models.ForeignKey(Presupuesto, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    descripcion = models.CharField(max_length=255)  # copia del nombre al momento de presupuestar
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    metros_por_caja = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    metros_totales = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    precio_m2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.descripcion} x {self.cantidad}"