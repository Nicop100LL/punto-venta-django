import ssl
from requests import Session
from zeep.transports import Transport
from zeep import Client

WSFE_URL_HOMO = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?wsdl"
WSFE_URL_PROD = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?wsdl"


import ssl
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from zeep.transports import Transport
from zeep import Client



class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()

        # 🔥 bajar seguridad para ARCA
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')

        # 🔥 clave para evitar el error actual
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

def get_client(modo="homologacion"):
    url = WSFE_URL_HOMO if modo == "homologacion" else WSFE_URL_PROD

    session = Session()

    # ❌ sacá esto:
    # session.verify = False

    session.mount("https://", SSLAdapter())

    transport = Transport(session=session)

    return Client(url, transport=transport)

def obtener_ultimo_numero(client, token, sign, cuit, punto_venta, tipo_cbte):
    resultado = client.service.FECompUltimoAutorizado(
        Auth={"Token": token, "Sign": sign, "Cuit": cuit},
        PtoVta=punto_venta,
        CbteTipo=tipo_cbte,
    )
    return resultado.CbteNro
def enviar_comprobante(client, token, sign, cuit, datos):
    
    # Tomar valor absoluto siempre (NC viene negativo, ARCA necesita positivo)
    total = abs(datos["total"])
    
    # Determinar alícuota según tipo de comprobante
    # NC de facturas viejas (21%) vs comprobantes nuevos (10.5%)
    es_nc = datos.get("comprobante_asociado") is not None
    
    if es_nc:
        divisor = 1.21   # Las facturas originales tienen IVA 21%
        id_iva  = 5      # ID 5 = 21%
    else:
        divisor = 1.105  # Comprobantes nuevos con IVA 10.5%
        id_iva  = 4      # ID 4 = 10.5%
    
    neto = round(total / divisor, 2)
    iva  = round(total - neto, 2)
    
    detalle = {
        "Concepto": 1,
        "DocTipo": datos["doc_tipo"],
        "DocNro": datos["doc_nro"],
        "CbteDesde": datos["numero"],
        "CbteHasta": datos["numero"],
        "CbteFch": datos["fecha"],
        "ImpTotal": total,   # ← abs(), siempre positivo
        "ImpTotConc": 0,
        "ImpNeto": neto,
        "ImpOpEx": 0,
        "ImpIVA": iva,
        "ImpTrib": 0,
        "MonId": "PES",
        "MonCotiz": 1,
        "Iva": {
            "AlicIva": [{
                "Id": id_iva,
                "BaseImp": neto,
                "Importe": iva,
            }]
        },
    }
    
    if datos.get("comprobante_asociado"):
        detalle["CbtesAsoc"] = {
            "CbteAsoc": [{
                "Tipo": datos["comprobante_asociado"]["tipo"],
                "PtoVta": datos["comprobante_asociado"]["pto_vta"],
                "Nro": datos["comprobante_asociado"]["nro"],
            }]
        }
    
    resultado = client.service.FECAESolicitar(
        Auth={"Token": token, "Sign": sign, "Cuit": cuit},
        FeCAEReq={
            "FeCabReq": {
                "CantReg": 1,
                "PtoVta": datos["punto_venta"],
                "CbteTipo": datos["tipo_cbte"],
            },
            "FeDetReq": {
                "FECAEDetRequest": [detalle]
            }
        }
    )
    
    print("RESPUESTA COMPLETA:")
    from zeep.helpers import serialize_object
    print(serialize_object(resultado))
    
    if resultado.Errors:
        errs = serialize_object(resultado.Errors)
        mensajes = [f"[{e['Code']}] {e['Msg']}" for e in errs.get('Err', [])]
        raise Exception(f"Error ARCA: {', '.join(mensajes)}")

    det_resp = resultado.FeDetResp.FECAEDetResponse[0]

    if det_resp.Resultado != "A":
        errores = []
        if det_resp.Observaciones:
            try:
                for obs in det_resp.Observaciones.Obs:
                    errores.append(f"[{obs.Code}] {obs.Msg}")
            except Exception:
                errores.append(str(det_resp.Observaciones))
        if not errores:
            errores.append(f"Resultado: {det_resp.Resultado}")
        raise Exception(f"ARCA rechazó el comprobante: {', '.join(errores)}")

    return {
        "cae":        det_resp.CAE,
        "vencimiento": det_resp.CAEFchVto,
        "numero":     datos["numero"],
    }