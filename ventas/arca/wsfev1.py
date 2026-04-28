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

        # 🔥 ESTA ES LA CLAVE
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')

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

    if datos["tipo_cbte"] in [6, 8]:  # Factura B o NC B
        neto = round(datos["total"] / 1.105, 2)
        iva  = round(datos["total"] - neto, 2)
        iva_id = 4  # 👈 10.5%
    else:
        neto = datos["total"]
        iva = 0
        iva_id = None

    fe_detalle = {
        "Concepto": 1,
        "DocTipo": datos["doc_tipo"],
        "DocNro": datos["doc_nro"],
        "CbteDesde": datos["numero"],
        "CbteHasta": datos["numero"],
        "CbteFch": datos["fecha"],
        "ImpTotal": datos["total"],
        "ImpTotConc": 0,
        "ImpNeto": neto,
        "ImpOpEx": 0,
        "ImpIVA": iva,
        "ImpTrib": 0,
        "MonId": "PES",
        "MonCotiz": 1,
        "CondicionIVAReceptorId": datos.get("condicion_iva_receptor", 5),
    }

    if iva_id:
        fe_detalle["Iva"] = {
            "AlicIva": [{
                "Id": iva_id,
                "BaseImp": neto,
                "Importe": iva,
            }]
        }

    if datos.get("cbtes_asoc"):
        fe_detalle["CbtesAsoc"] = {
            "CbteAsoc": datos["cbtes_asoc"]
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
                "FECAEDetRequest": [fe_detalle]
            }
        }
    )