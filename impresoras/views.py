from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from .models import ConfiguracionImpresoraTicket


@login_required
def test_ticket(request):
    try:
        config = request.user.empresa.config_impresora_ticket
    except ConfiguracionImpresoraTicket.DoesNotExist:
        return HttpResponseBadRequest("No hay impresora configurada")

    payload = {
        "tipo": "test",
        "empresa": request.user.empresa.nombre,
        "impresora": config.nombre_sistema,
        "ancho_mm": config.ancho_mm,
        "cortar_papel": config.cortar_papel,
        "abrir_cajon": config.abrir_cajon,
        "contenido": [
            {"tipo": "center", "texto": "=== TICKET DE PRUEBA ==="},
            {"tipo": "line"},
            {"tipo": "text", "texto": f"Empresa: {request.user.empresa.nombre}"},
            {"tipo": "text", "texto": "Prueba de impresión"},
            {"tipo": "text", "texto": "----------------------"},
            {"tipo": "center", "texto": "OK SI SE LEE BIEN"},
            {"tipo": "line"},
            {"tipo": "text", "texto": "Fin del ticket"},
        ]
    }

    return JsonResponse(payload)
