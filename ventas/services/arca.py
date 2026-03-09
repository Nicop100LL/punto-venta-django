def enviar_a_arca(comprobante):

    empresa = comprobante.venta.empresa

    if not empresa.usa_arca:
        raise Exception("Empresa no configurada para ARCA")

    cuit = empresa.cuit
    punto_venta = empresa.arca_punto_venta

    # aquí irá el login WSAA
    # luego la creación del comprobante

    return {
        "cae": "SIM-123456",
        "numero": 1,
        "vencimiento": "2026-03-30"
    }
    


from ventas.models import ReglaArcaPago, ComprobanteArca

def decidir_arca(venta):
    """
    Decide si una venta debe subirse a ARCA según reglas.
    NO envía nada.
    """

    empresa = venta.empresa

    if not empresa.usa_arca:
        return {
            "subir_a_arca": False
        }
        
    # 1️⃣ Buscar regla para ese medio de pago y empresa
    regla = ReglaArcaPago.objects.filter(
        empresa=venta.empresa,
        tipo_pago=venta.tipo_pago
    ).first()

    # 2️⃣ Si no hay regla → no ARCA
    if not regla or not regla.subir_a_arca:
        return {
            "subir_a_arca": False,
            "obligatorio": False,
            "tipo": None,
        }

    # 3️⃣ Validaciones mínimas
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

    