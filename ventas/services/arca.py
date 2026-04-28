# ventas/services/arca.py
from ventas.arca.wsaa import obtener_token
from ventas.arca.wsfev1 import get_client, obtener_ultimo_numero, enviar_comprobante
from ventas.models import ReglaArcaPago, ComprobanteArca

TIPO_CBT = {
    "cf":        6,  # Factura C / Consumidor Final
    "boleta":    6,
    "factura_a":  1,  # Factura A
    "factura_b":  6,  # Factura B
    
    "nota_credito_a": 3,
    "nota_credito_b": 8,
    "nota_credito_cf": 8,
}


def enviar_a_arca(comprobante):

    empresa = comprobante.venta.empresa

    if not empresa.usa_arca:
        raise Exception("Empresa no configurada para ARCA")

    # Rutas a los archivos del certificado
    cert_path = empresa.arca_certificado.path
    key_path  = empresa.arca_clave_privada.path
    modo      = empresa.arca_modo
    cuit      = empresa.cuit.replace("-", "")
    punto_venta = empresa.arca_punto_venta

    # 1. Login WSAA — obtener token y sign
    token, sign = obtener_token(cert_path, key_path, modo=modo, empresa=empresa)

    # 2. Conectar al WSFEv1
    client = get_client(modo=modo)

    # 3. Tipo de comprobante numérico
    tipo_cbte = TIPO_CBT.get(comprobante.tipo)
    if not tipo_cbte:
        raise Exception(f"Tipo de comprobante desconocido: {comprobante.tipo}")

    # 4. Obtener próximo número
    ultimo = obtener_ultimo_numero(client, token, sign, cuit, punto_venta, tipo_cbte)
    numero = ultimo + 1

    # 5. Datos del cliente
    venta = comprobante.venta
    if venta.cliente and venta.cliente.cuit:
        doc_tipo = 80   # CUIT
        doc_nro  = int(venta.cliente.cuit.replace("-", ""))
    else:
        doc_tipo = 99   # Consumidor Final
        doc_nro  = 0

    # 6. Fecha en formato YYYYMMDD
    fecha = venta.fecha.strftime("%Y%m%d")

    # 7. Enviar
    respuesta = enviar_comprobante(client, token, sign, cuit, {
        "punto_venta": punto_venta,
        "tipo_cbte":   tipo_cbte,
        "doc_tipo":    doc_tipo,
        "doc_nro":     doc_nro,
        "numero":      numero,
        "fecha":       fecha,
        "total":       float(venta.total),
    })

    return {
        "cae":       respuesta["cae"],
        "numero":    respuesta["numero"],
        "vencimiento": respuesta["vencimiento"],
    }


def decidir_arca(venta):
    """
    Decide si una venta debe subirse a ARCA según reglas.
    NO envía nada.
    """
    empresa = venta.empresa

    if not empresa.usa_arca:
        return {"subir_a_arca": False}

    regla = ReglaArcaPago.objects.filter(
        empresa=venta.empresa,
        tipo_pago=venta.tipo_pago
    ).first()

    if not regla or not regla.subir_a_arca:
        return {
            "subir_a_arca": False,
            "obligatorio": False,
            "tipo": None,
        }

    if regla.tipo_comprobante in ("factura_a", "factura_b"):
        if not venta.cliente or not venta.cliente.cuit:
            return {
                "subir_a_arca": False,
                "error": "El cliente no tiene CUIT",
            }

    return {
        "subir_a_arca": True,
        "obligatorio": False,
        "tipo": regla.tipo_comprobante
    }