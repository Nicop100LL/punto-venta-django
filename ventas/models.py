from django.db import models
from productos.models import Producto
from usuarios.models import Usuario, Empresa
from django.utils import timezone

TIPO_COMPROBANTE_CHOICES = [
    ('ticket', 'Consumidor Final (Ticket)'),
    ('factura_afip', 'Factura AFIP'),
]


class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    cuit = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    saldo = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    cuenta_corriente = models.BooleanField(default=True)

    condicion_iva = models.CharField(max_length=50, choices=[
        ('RI', 'Responsable Inscripto'),
        ('MT', 'Monotributista'),
        ('CF', 'Consumidor Final'),
        ('EX', 'Exento'),
    ], default='CF')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre
    

class Venta(models.Model):
    fecha = models.DateTimeField(default=timezone.now)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cuenta_corriente = models.BooleanField(default=False)
    tipo_comprobante = models.CharField(
        max_length=20,
        choices=TIPO_COMPROBANTE_CHOICES,
        default='ticket'
    )

    TIPO_PAGO_CHOICES = [
        ('EF', 'Efectivo'),
        ('MP', 'QR (Mercado Pago)'),
        ('DN', 'QR (Cuenta DNI)'),
        ('TJ', 'Tarjeta'),
        ('TR', 'Transferencia'),
    ]

    tipo_pago = models.CharField(
        max_length=2,
        choices=TIPO_PAGO_CHOICES,
        default='EF'
    )

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha.date()}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def descuento_aplicado(self):
        # Suponiendo que la cantidad mínima para el descuento es un atributo del producto
        if self.cantidad >= self.producto.cantidad_minima_para_descuento:
            # Calculamos el descuento aplicado
            descuento = self.producto.descuento  # Supongamos que el descuento es un porcentaje
            return (self.precio_unitario * descuento / 100) * self.cantidad
        return 0  # Si no se cumple la cantidad mínima, no hay descuento
    
    def subtotal_con_descuento(self):
        # Calculamos el subtotal considerando el descuento
        return self.subtotal() - self.descuento_aplicado()

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"

