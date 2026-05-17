from django.db import models
from productos.models import Producto
from usuarios.models import Usuario, Empresa
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from caja.models import CierreCaja


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
    nota = models.TextField(blank=True, null=True)  
    caja = models.ForeignKey(
        CierreCaja,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventas'
    )

    # 🔥 NUEVO: número correlativo por empresa
    numero_empresa = models.PositiveIntegerField(default=1)

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
    
    # ✅ NUEVO – efectivo
    importe_entregado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    vuelto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha.date()}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    detalle = models.CharField(max_length=255, blank=True, default='')
    precio_compra = models.DecimalField(max_digits=10, decimal_places=3, default=0)

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

class PagoCliente(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pagos')
    fecha = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=[('total', 'Total'), ('parcial', 'Parcial')])
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)


    def __str__(self):
        return f"{self.cliente.nombre} - {self.tipo} - {self.monto} ({self.fecha})"
    


class NotaCredito(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name='notas_credito')
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    motivo = models.TextField(blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=[('pendiente', 'Pendiente'), ('aplicada', 'Aplicada'), ('cancelada', 'Cancelada')],
        default='pendiente'
    )
    caja = models.ForeignKey(
        'caja.CierreCaja',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notas_credito'
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Nota de Crédito #{self.id} - Venta #{self.venta.id}"


class DetalleNotaCredito(models.Model):
    nota_credito = models.ForeignKey(
        NotaCredito,
        related_name='detalles',
        on_delete=models.CASCADE
    )
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

class ComprobanteArca(models.Model):

    venta = models.OneToOneField(
        Venta,
        on_delete=models.CASCADE,
        related_name="comprobante_arca"
    )

    tipo = models.CharField(
        max_length=30,
        choices=[
            ("cf",        "Consumidor Final"),
            ("boleta",    "Boleta Común"),
            ("factura_a", "Factura A"),
            ("factura_b", "Factura B"),
            ("nc_a",      "Nota de Crédito A"),  # ← agregar
            ("nc_b",      "Nota de Crédito B"),  # ← agregar
            ("nc_c",      "Nota de Crédito C"),  # ← agregar
        ]
    )

    numero = models.IntegerField(blank=True, null=True)

    estado = models.CharField(
        max_length=20,
        db_index=True,
        choices=[
            ("pendiente", "Pendiente"),
            ("aprobado",  "Aprobado"),
            ("error",     "Error"),
        ],
        default="pendiente"
    )

    cae = models.CharField(max_length=50, blank=True, null=True)
    vencimiento_cae = models.DateField(blank=True, null=True)
    mensaje_error = models.TextField(blank=True, null=True)
    procesando = models.BooleanField(default=False)
    intentos = models.IntegerField(default=0)
    ultimo_intento = models.DateTimeField(blank=True, null=True)
    enviado_en = models.DateTimeField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    raw_response = models.JSONField(blank=True, null=True)

    comprobante_asociado_tipo = models.IntegerField(
        blank=True, null=True,
        help_text="Tipo del comprobante que se anula (para NC)"
    )
    comprobante_asociado_pto_vta = models.IntegerField(
        blank=True, null=True,
        help_text="Punto de venta del comprobante original"
    )
    comprobante_asociado_nro = models.IntegerField(
        blank=True, null=True,
        help_text="Número del comprobante que se anula"
    )

    def puede_reintentar(self):
        return self.intentos < 3

class TokenArca(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="tokens_arca"
    )
    servicio = models.CharField(max_length=20, default="wsfe")
    modo = models.CharField(max_length=20, default="homologacion")
    token = models.TextField()
    sign = models.TextField()
    expira = models.DateTimeField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("empresa", "servicio", "modo")

    def es_valido(self):
        from django.utils import timezone
        return timezone.now() < self.expira

    def __str__(self):
        return f"Token {self.empresa} - {self.servicio} - {self.modo}"

class ReglaArcaPago(models.Model):

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    tipo_pago = models.CharField(
        max_length=2,
        choices=Venta.TIPO_PAGO_CHOICES
    )

    subir_a_arca = models.BooleanField(default=False)

    tipo_comprobante = models.CharField(
        max_length=30,
        choices=[
            ("cf", "Consumidor Final"),
            ("boleta", "Boleta Común"),
            ("factura_a", "Factura A"),
            ("factura_b", "Factura B"),
        ],
        blank=True,
        null=True
    )

    obligatorio = models.BooleanField(default=False)

    class Meta:
        unique_together = ("empresa", "tipo_pago")    
        
        
class EgresoCaja(models.Model):
    TIPO_CHOICES = [
        ('proveedor', 'Pago a Proveedor'),
        ('servicio', 'Servicio (luz, agua, internet)'),
        ('alquiler', 'Alquiler'),
        ('sueldo', 'Sueldo/Honorarios'),
        ('impuesto', 'Impuesto/Tasas'),
        ('varios', 'Otros Gastos'),
    ]
    
    METODO_PAGO_CHOICES = [
        ('EF', 'Efectivo'),
        ('TR', 'Transferencia'),
        ('TJ', 'Tarjeta'),
    ]
    
    caja = models.ForeignKey(
        'caja.CierreCaja',
        on_delete=models.PROTECT,
        related_name='egresos',
        null=True,
        blank=True
    )
    
    fecha = models.DateTimeField(default=timezone.now)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='varios')
    concepto = models.CharField(max_length=200, help_text="Ej: Pago a Distribuidora XYZ")
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=2, choices=METODO_PAGO_CHOICES, default='EF')
    
    proveedor = models.CharField(max_length=100, blank=True)
    comprobante = models.CharField(max_length=50, blank=True)
    observaciones = models.TextField(blank=True)
    
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Egreso de Caja'
        verbose_name_plural = 'Egresos de Caja'
    
    def __str__(self):
        return f"Egreso {self.get_tipo_display()} - ${self.monto} ({self.fecha.date()})"        