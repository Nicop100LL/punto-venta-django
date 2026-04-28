# ventas/arca/service.py
from ventas.arca.wsaa import obtener_token
from ventas.arca.wsfev1 import get_client, obtener_ultimo_numero, enviar_comprobante
from ventas.models import ReglaArcaPago, ComprobanteArca
from ventas.models import NotaCredito, DetalleNotaCredito
from datetime import datetime

TIPO_CBT = {
    "cf":        6,
    "boleta":    6,
    "ticket":    6,
    "factura_a": 1,
    "factura_b": 6,
    
    "nota_credito_a": 3,
    "nota_credito_b": 8,
    "nota_credito_cf": 8,
}


def enviar_a_arca(comprobante):

    empresa = comprobante.venta.empresa

    if not empresa.usa_arca:
        raise Exception("Empresa no configurada para ARCA")

    cert_path   = empresa.arca_certificado.path
    key_path    = empresa.arca_clave_privada.path
    modo        = empresa.arca_modo
    cuit        = empresa.cuit.replace("-", "")
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

    fecha = datetime.now().strftime("%Y%m%d")

    print("CUIT:", cuit)
    print("Punto de venta:", punto_venta)
    print("Tipo comprobante:", tipo_cbte)
    print("Tipo original:", comprobante.tipo)
    
    data = {
        "punto_venta": punto_venta,
        "tipo_cbte": tipo_cbte,
        "doc_tipo": doc_tipo,
        "doc_nro": doc_nro,
        "numero": numero,
        "fecha": fecha,
        "total": float(venta.total),
    }

    # 🔥 SOLO si tiene CUIT
    if doc_tipo == 80:
        data["condicion_iva_receptor"] = 5  # ajustar después si hace falta

    respuesta = enviar_comprobante(client, token, sign, cuit, data)

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
    
    

def crear_nc_y_enviar(venta, usuario):

    from ventas.models import NotaCredito
    from ventas.arca.wsaa import obtener_token
    from ventas.arca.wsfev1 import get_client, obtener_ultimo_numero, enviar_comprobante

    empresa = venta.empresa
    comp = venta.comprobante_arca

    if not comp or comp.estado != "aprobado":
        print(f"Venta {venta.id} sin comprobante válido")
        return

    # 🔐 Datos ARCA
    cert_path = empresa.arca_certificado.path
    key_path  = empresa.arca_clave_privada.path
    modo      = empresa.arca_modo
    cuit      = empresa.cuit.replace("-", "")
    punto_venta = empresa.arca_punto_venta

    token, sign = obtener_token(cert_path, key_path, modo=modo, empresa=empresa)
    client = get_client(modo=modo)

    # 👤 Cliente
    if venta.cliente and venta.cliente.cuit:
        doc_tipo = 80
        doc_nro  = int(venta.cliente.cuit.replace("-", ""))
    else:
        doc_tipo = 99
        doc_nro  = 0

    fecha = datetime.now().strftime("%Y%m%d")

    # 🧾 Tipo NC
    tipo_nc_map = {
        "factura_a": "nota_credito_a",
        "factura_b": "nota_credito_b",
        "cf": "nota_credito_cf",
        "boleta": "nota_credito_cf",
        
        "ticket": "nota_credito_cf",
        "factura_afip": "nota_credito_b",
    }

    tipo_nc = tipo_nc_map.get(comp.tipo)

    if not tipo_nc:
        print(f"No se pudo determinar tipo NC para venta {venta.id}")
        return

    tipo_cbte_nc = TIPO_CBT[tipo_nc]

    # 🔢 Número comprobante
    ultimo = obtener_ultimo_numero(client, token, sign, cuit, punto_venta, tipo_cbte_nc)
    numero = ultimo + 1

    # 🧾 Crear NC local
    nc = NotaCredito.objects.create(
        venta=venta,
        cliente=venta.cliente,
        total=venta.total,
        motivo="Corrección IVA 21% -> 10.5%",
        usuario=usuario
    )

    # 🚀 Enviar a ARCA
    resultado = enviar_comprobante(client, token, sign, cuit, {
        "punto_venta": punto_venta,
        "tipo_cbte": tipo_cbte_nc,
        "doc_tipo": doc_tipo,
        "doc_nro": doc_nro,
        "numero": numero,
        "fecha": fecha,
        "total": float(nc.total),

        # 🔥 CLAVE: asociar comprobante original
        "cbtes_asoc": [
            {
                "Tipo": TIPO_CBT[comp.tipo],
                "PtoVta": punto_venta,
                "Nro": int(comp.numero),
            }
        ]
    })

    print(f"✅ NC creada OK para venta {venta.id} - CAE: {resultado['cae']}")