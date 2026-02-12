# views.py en app impresoras

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from .models import ConfiguracionImpresoraTicket

@login_required
def test_ticket(request):
    """
    Genera un ticket de prueba en formato JSON listo para el microservicio ESC/POS.
    """
    try:
        config = request.user.empresa.config_impresora_ticket
    except ConfiguracionImpresoraTicket.DoesNotExist:
        return HttpResponseBadRequest("No hay impresora configurada")

    # Ticket base
    contenido = [
        {"tipo": "center", "bold": True, "size": "lg", "texto": "=== TICKET DE PRUEBA ==="},
        {"tipo": "line"},
        {"tipo": "text", "texto": f"Empresa: {request.user.empresa.nombre}"},
        {"tipo": "text", "texto": "Prueba de impresión"},
        {"tipo": "line"},
        {"tipo": "center", "texto": "OK SI SE LEE BIEN"},
        {"tipo": "line"},
        {"tipo": "text", "texto": "Fin del ticket"},
    ]

    # Insertar logo al inicio si existe
    if config.logo:
        contenido.insert(0, {"tipo": "image", "path": config.logo.url, "align": "center"})

    # Agregar datos de la empresa
    if config.datos_empresa:
        contenido.append({"tipo": "text", "texto": config.datos_empresa})

    # Agregar saludo final
    if config.saludo_final:
        contenido.append({"tipo": "center", "bold": True, "texto": config.saludo_final})

    payload = {
        "tipo": "test",
        "empresa": request.user.empresa.nombre,
        "impresora": config.nombre_sistema,
        "ancho_mm": config.ancho_mm,
        "cortar_papel": config.cortar_papel,
        "abrir_cajon": config.abrir_cajon,
        "contenido": contenido
    }

    return JsonResponse(payload)


# views.py
from django.views.decorators.http import require_POST
from ventas.models import Venta
from django.shortcuts import get_object_or_404
import requests

@login_required
@require_POST
def enviar_ticket(request, venta_id):
    """
    Enviar ticket al microservicio ESC/POS si está configurado,
    si no, usar fallback de impresión por navegador.
    """
    venta = get_object_or_404(Venta, id=venta_id)
    config = request.user.empresa.config_impresora_ticket

    # Construimos el JSON como el test_ticket, pero con datos reales
    contenido = [
        {"tipo": "center", "bold": True, "size": "lg", "texto": f"TICKET #{venta.numero_empresa}"},
        {"tipo": "line"},
        {"tipo": "text", "texto": f"Cliente: {venta.cliente.nombre if venta.cliente else 'Consumidor Final'}"},
        {"tipo": "text", "texto": f"Total: ${venta.total}"},
        {"tipo": "line"},
    ]
    # Podés agregar más detalles de la venta: productos, subtotal, pago, etc.

    payload = {
        "tipo": "venta",
        "empresa": request.user.empresa.nombre,
        "impresora": config.nombre_sistema,
        "ancho_mm": config.ancho_mm,
        "cortar_papel": config.cortar_papel,
        "abrir_cajon": config.abrir_cajon,
        "contenido": contenido
    }

    if config.microservicio_url:
        try:
            r = requests.post(f"{config.microservicio_url}", json=payload, timeout=3)
            r.raise_for_status()
            return JsonResponse({"status": "ok", "message": "Ticket enviado al microservicio"})
        except requests.RequestException as e:
            # Fallback
            return JsonResponse({"status": "error", "message": f"No se pudo imprimir vía microservicio: {e}"})
    
    # Si no hay microservicio configurado, fallback a window.print()
    return JsonResponse({"status": "fallback", "message": "Impresión por navegador"})
