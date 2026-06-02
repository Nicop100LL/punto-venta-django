# ventas/arca/service.py
from ventas.arca.wsaa import obtener_token
from ventas.arca.wsfev1 import get_client, obtener_ultimo_numero, enviar_comprobante
from ventas.models import ReglaArcaPago, ComprobanteArca

TIPO_CBT = {
    "cf":        11,  # Factura C / Consumidor Final
    "boleta":    11,
    "factura_a":  1,  # Factura A
    "factura_b":  6,  # Factura B
    "nc_a":      3,   # Nota de Crédito A
    "nc_b":      8,   # Nota de Crédito B
    "nc_c":     13,
}


def enviar_a_arca(comprobante):

    empresa = comprobante.venta.empresa

    if not empresa.usa_arca:
        raise Exception("Empresa no configurada para ARCA")

    cert_path = empresa.arca_certificado.path
    key_path  = empresa.arca_clave_privada.path
    modo      = empresa.arca_modo
    cuit      = empresa.cuit.replace("-", "")
    punto_venta = empresa.arca_punto_venta

    token, sign = obtener_token(cert_path, key_path, modo=modo, empresa=empresa)
    client = get_client(modo=modo)

    tipo_cbte = TIPO_CBT.get(comprobante.tipo)
    if not tipo_cbte:
        raise Exception(f"Tipo de comprobante desconocido: {comprobante.tipo}")

    ultimo = obtener_ultimo_numero(client, token, sign, cuit, punto_venta, tipo_cbte)
    numero = ultimo + 1

    venta = comprobante.venta
    if venta.cliente and venta.cliente.cuit:
        doc_tipo = 80
        doc_nro  = int(venta.cliente.cuit.replace("-", ""))
    else:
        doc_tipo = 99
        doc_nro  = 0

    fecha = venta.fecha.strftime("%Y%m%d")

    # Armar datos por separado para poder agregar el asociado si es NC
    datos_envio = {
        "punto_venta": punto_venta,
        "tipo_cbte":   tipo_cbte,
        "doc_tipo":    doc_tipo,
        "doc_nro":     doc_nro,
        "numero":      numero,
        "fecha":       fecha,
        "total":       float(venta.total),
    }

    # Solo para NC: agregar referencia al comprobante original
    if comprobante.tipo.startswith('nc_') and comprobante.comprobante_asociado_nro:
        datos_envio["comprobante_asociado"] = {
            "tipo":    comprobante.comprobante_asociado_tipo,
            "pto_vta": comprobante.comprobante_asociado_pto_vta,
            "nro":     comprobante.comprobante_asociado_nro,
        }

    respuesta = enviar_comprobante(client, token, sign, cuit, datos_envio)

    return {
        "cae":        respuesta["cae"],
        "numero":     respuesta["numero"],
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

    if not regla.tipo_comprobante:
        return {
            "subir_a_arca": False,
            "obligatorio": False,
            "tipo": None,
            "error": "Regla ARCA sin tipo de comprobante configurado",
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