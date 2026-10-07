from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import AgenteBalanza, Balanza, CambioBalanza

LOTE = 50
MAX_INTENTOS = 5


class AgenteAuth(BaseAuthentication):
    def authenticate(self, request):
        h = request.headers.get('Authorization', '')
        if not h.startswith('Bearer '):
            return None
        digest = AgenteBalanza.hashear(h[7:].strip())
        try:
            agente = AgenteBalanza.objects.select_related('empresa').get(
                token_hash=digest, activo=True, empresa__usa_balanza=True)
        except AgenteBalanza.DoesNotExist:
            raise AuthenticationFailed('Token inválido')
        return (agente, None)

    def authenticate_header(self, request):
        return 'Bearer'


class EsAgente(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, AgenteBalanza)


class _Base(APIView):
    authentication_classes = [AgenteAuth]
    permission_classes = [EsAgente]


class Pendientes(_Base):
    def get(self, request):
        agente = request.user
        AgenteBalanza.objects.filter(pk=agente.pk).update(ultimo_latido=timezone.now())
        salida = []
        for b in Balanza.objects.filter(agente=agente, empresa=agente.empresa, activa=True):
            cambios = b.cambios.filter(estado='pendiente').order_by('id')[:LOTE]
            salida.append({
                'id': b.id, 'nombre': b.nombre, 'direccion_equipo': b.direccion_equipo,
                'tipo_conexion': b.tipo_conexion, 'ip': b.ip, 'puerto': b.puerto,
                'puerto_com': b.puerto_com, 'decimales_precio': b.decimales_precio,
                'sector': b.sector_por_defecto,
                'cambios': [{'id': c.id, 'plu': c.plu, 'tipo': c.tipo, 'nombre': c.nombre,
                             'precio': str(c.precio), 'tipo_venta': c.tipo_venta,
                             'version': c.version} for c in cambios],
            })
        return Response({'balanzas': salida})


class Confirmar(_Base):
    def post(self, request, pk):
        c = get_object_or_404(CambioBalanza, pk=pk, balanza__agente=request.user,
                              balanza__empresa=request.user.empresa)
        if c.estado != 'pendiente':
            return Response({'estado': c.estado})
        version = request.data.get('version')
        if version is not None and str(version) != str(c.version):
            return Response({'estado': 'pendiente', 'nota': 'cambió mientras se enviaba'})
        if request.data.get('ok'):
            c.estado, c.error_detalle = 'enviado', ''
            c.sincronizado_en = timezone.now()
        else:
            c.intentos += 1
            c.error_detalle = str(request.data.get('error', ''))[:255]
            if request.data.get('definitivo') or c.intentos >= MAX_INTENTOS:
                c.estado = 'error'
        c.save()
        return Response({'estado': c.estado})


class Latido(_Base):
    def post(self, request):
        ahora = timezone.now()
        AgenteBalanza.objects.filter(pk=request.user.pk).update(ultimo_latido=ahora)
        for it in request.data.get('balanzas', []):
            qs = Balanza.objects.filter(pk=it.get('id'), agente=request.user)
            cambios = {'ultimo_estado': str(it.get('detalle', ''))[:80]}
            if it.get('ok'):
                cambios['ultima_comunicacion'] = ahora
            qs.update(**cambios)
        return Response({'ok': True})
