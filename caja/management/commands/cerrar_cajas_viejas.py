from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from caja.models import CierreCaja
from ventas.models import Venta, NotaCredito, EgresoCaja


class Command(BaseCommand):
    help = "Cierra automáticamente las cajas abiertas hace más de N horas."

    def add_arguments(self, parser):
        parser.add_argument('--horas', type=int, default=24)
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo muestra qué cajas se cerrarían')

    def handle(self, *args, **opts):
        limite = timezone.now() - timedelta(hours=opts['horas'])
        cajas = CierreCaja.objects.filter(
            estado='abierta', fecha_apertura__lt=limite
        ).select_related('empresa', 'usuario')

        for caja in cajas:
            if opts['dry_run']:
                self.stdout.write(
                    f"[DRY] caja {caja.id} {caja.empresa} {caja.usuario} "
                    f"abierta desde {caja.fecha_apertura}"
                )
                continue
            try:
                with transaction.atomic():
                    self.cerrar(caja)
                self.stdout.write(self.style.SUCCESS(
                    f"Cerrada caja {caja.id} ({caja.empresa})"))
            except Exception as e:
                self.stderr.write(f"ERROR caja {caja.id}: {e}")

    def cerrar(self, caja):
        ventas = Venta.objects.filter(caja=caja)

        total_ef = ventas.filter(
            tipo_pago='EF', cuenta_corriente=False
        ).aggregate(t=Sum('total'))['t'] or Decimal('0')

        nc_ef = NotaCredito.objects.filter(
            caja=caja, estado='aplicada', venta__tipo_pago='EF'
        ).aggregate(t=Sum('total'))['t'] or Decimal('0')

        egresos = EgresoCaja.objects.filter(
            caja=caja
        ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

        esperado = caja.monto_inicial + total_ef - nc_ef - egresos

        caja.fecha_cierre = timezone.now()
        caja.efectivo_sistema = esperado
        caja.efectivo_real = esperado
        caja.saldo_final = esperado
        caja.diferencia = Decimal('0')
        caja.estado = 'cerrada'
        caja.observaciones = (
            (caja.observaciones + "\n" if caja.observaciones else "")
            + "Cierre automático (sin conteo físico)."
        )
        caja.save()