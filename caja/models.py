from django.db import models
from django.conf import settings
from usuarios.models import Usuario, Empresa
from django.db.models import Sum
from django.utils import timezone

class CierreCaja(models.Model):
    ESTADO_CHOICES = [
        ('abierta', 'Abierta'),
        ('cerrada', 'Cerrada'),
    ]

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='cierres_caja'
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='cierres_caja'
    )

    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    monto_inicial = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    efectivo_sistema = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    efectivo_real = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    diferencia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='abierta'
    )
    saldo_final = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )


    observaciones = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_apertura']
        verbose_name = 'Cierre de Caja'
        verbose_name_plural = 'Cierres de Caja'

    def __str__(self):
        return f"Caja {self.usuario} - {self.fecha_apertura.strftime('%d/%m/%Y %H:%M')}"

    # ======================
    # MÉTODOS DE TOTALES
    # ======================

    def total_general(self):
        return self.ventas.aggregate(
            total=Sum('total')
        )['total'] or 0

    def total_por_tipo_pago(self, tipo):
        return self.ventas.filter(
            tipo_pago=tipo
        ).aggregate(
            total=Sum('total')
        )['total'] or 0

    def total_efectivo(self):
        return self.total_por_tipo_pago('EF')

    def total_qr(self):
        return self.ventas.filter(
            tipo_pago__in=['MP', 'DN']
        ).aggregate(
            total=Sum('total')
        )['total'] or 0

    def total_tarjeta(self):
        return self.total_por_tipo_pago('TJ')

    def total_transferencia(self):
        return self.total_por_tipo_pago('TR')

    def total_cuenta_corriente(self):
        return self.ventas.filter(
            cuenta_corriente=True
        ).aggregate(
            total=Sum('total')
        )['total'] or 0
