# ventas/arca/service.py
from ventas.arca.wsaa import obtener_token
from ventas.arca.wsfev1 import get_client, obtener_ultimo_numero, enviar_comprobante
from ventas.models import ReglaArcaPago, ComprobanteArca


TIPO_CBT = {
    "cf":        11,
    "boleta":    11,
    "factura_a":  1,
    "factura_b":  6,
    "nc_a":       3,
    "nc_b":       8,
    "nc_c":      13,
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

    datos_envio = {
        "punto_venta": punto_venta,
        "tipo_cbte":   tipo_cbte,
        "doc_tipo":    doc_tipo,
        "doc_nro":     doc_nro,
        "numero":      numero,
        "fecha":       fecha,
        "total":       float(venta.total),
        "alicuota_iva": float(comprobante.alicuota_iva or empresa.arca_alicuota_iva_default),
    }
    
    # ⬇️ AGREGAR: Si es NC, incluir comprobante asociado
    if comprobante.tipo.startswith('nc_') and comprobante.comprobante_asociado_nro:
        datos_envio["comprobante_asociado"] = {
            "tipo": comprobante.comprobante_asociado_tipo,
            "pto_vta": comprobante.comprobante_asociado_pto_vta,
            "nro": comprobante.comprobante_asociado_nro,
        }

    respuesta = enviar_comprobante(client, token, sign, cuit, datos_envio)

    return {
        "cae":        respuesta["cae"],
        "numero":     respuesta["numero"],
        "vencimiento": respuesta["vencimiento"],
    }


def decidir_arca(venta):
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
            "obligatorio":  False,
            "tipo":         None,
        }

    if regla.tipo_comprobante in ("factura_a", "factura_b"):
        if not venta.cliente or not venta.cliente.cuit:
            return {
                "subir_a_arca": False,
                "error": "El cliente no tiene CUIT",
            }

    return {
        "subir_a_arca": True,
        "obligatorio":  False,
        "tipo":         regla.tipo_comprobante
    }
    
def crear_nota_credito(venta_original, motivo="Anulación"):
    from ventas.models import Venta, ComprobanteArca
    from django.db import transaction
    from django.utils import timezone

    with transaction.atomic():
        # Con OneToOneField se accede así:
        try:
            comp_original = venta_original.comprobante_arca
        except ComprobanteArca.DoesNotExist:
            raise Exception("La venta no tiene comprobante ARCA")

        if comp_original.estado != "aprobado":
            raise Exception("El comprobante original no está aprobado")

        if comp_original.tipo in ('nc_a', 'nc_b', 'nc_c'):
            raise Exception("No se puede crear NC de una NC")

        # Verificar que no exista NC previa para este comprobante
        nc_existente = ComprobanteArca.objects.filter(
            comprobante_asociado_nro=comp_original.numero,
            comprobante_asociado_pto_vta=venta_original.empresa.arca_punto_venta,
            comprobante_asociado_tipo=TIPO_CBT[comp_original.tipo]
        ).exists()

        if nc_existente:
            raise Exception(f"Ya existe una NC para el comprobante {comp_original.numero}")

        tipo_nc_map = {
            "factura_a": "nc_a",
            "factura_b": "nc_b",
            "cf":        "nc_b",
            "boleta":    "nc_c",
        }
        tipo_nc = tipo_nc_map.get(comp_original.tipo)
        if not tipo_nc:
            raise Exception(f"No se puede crear NC para tipo {comp_original.tipo}")

        # Crear venta negativa
        venta_nc = Venta.objects.create(
            empresa=venta_original.empresa,
            cliente=venta_original.cliente,
            tipo_pago=venta_original.tipo_pago,
            total=-abs(venta_original.total),
            fecha=timezone.now(),
        )

        # Crear comprobante NC (OneToOneField: una venta → un comprobante)
        comp_nc = ComprobanteArca.objects.create(
            venta=venta_nc,
            tipo=tipo_nc,
            estado="pendiente",
            comprobante_asociado_tipo=TIPO_CBT[comp_original.tipo],
            comprobante_asociado_pto_vta=venta_original.empresa.arca_punto_venta,
            comprobante_asociado_nro=comp_original.numero,
            alicuota_iva=comp_original.alicuota_iva,
        )

        return comp_nc