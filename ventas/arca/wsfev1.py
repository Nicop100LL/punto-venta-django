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
    resultado = client.service.FECAESolicitar(
        Auth={"Token": token, "Sign": sign, "Cuit": cuit},
        FeCAEReq={
            "FeCabReq": {
                "CantReg": 1,
                "PtoVta": datos["punto_venta"],
                "CbteTipo": datos["tipo_cbte"],
            },
            "FeDetReq": {
                "FECAEDetRequest": [{
                    "Concepto": 1,
                    "DocTipo": datos["doc_tipo"],
                    "DocNro": datos["doc_nro"],
                    "CbteDesde": datos["numero"],
                    "CbteHasta": datos["numero"],
                    "CbteFch": datos["fecha"],
                    "ImpTotal": datos["total"],
                    "ImpTotConc": 0,
                    "ImpNeto": datos["total"],
                    "ImpOpEx": 0,
                    "ImpIVA": 0,
                    "ImpTrib": 0,
                    "MonId": "PES",
                    "MonCotiz": 1,
                    "Iva": None,
                    "CondicionIVAReceptorId": datos.get("condicion_iva_receptor", 5),
                }]
            }
        }
    )

    # Capturar errores de cabecera
    if resultado.Errors:
        from zeep.helpers import serialize_object
        errs = serialize_object(resultado.Errors)
        mensajes = [f"[{e['Code']}] {e['Msg']}" for e in errs.get('Err', [])]
        raise Exception(f"Error ARCA: {', '.join(mensajes)}")

    detalle = resultado.FeDetResp.FECAEDetResponse[0]

    if detalle.Resultado != "A":
        errores = []
        if detalle.Observaciones:
            try:
                for obs in detalle.Observaciones.Obs:
                    errores.append(f"[{obs.Code}] {obs.Msg}")
            except Exception:
                errores.append(str(detalle.Observaciones))
        if not errores:
            errores.append(f"Resultado: {detalle.Resultado}")
        raise Exception(f"ARCA rechazó el comprobante: {', '.join(errores)}")

    return {
        "cae":        detalle.CAE,
        "vencimiento": detalle.CAEFchVto,
        "numero":     datos["numero"],
    }