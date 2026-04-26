# ventas/arca/wsaa.py
import datetime
import base64
import xml.etree.ElementTree as ET
import zeep
from django.utils import timezone
import ssl

# Permitir DH keys pequeñas (necesario para AFIP)

ssl._create_default_https_context = ssl._create_unverified_context

WSAA_URL_HOMO = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
WSAA_URL_PROD = "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"


def crear_tra(servicio="wsfe"):
    ahora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    expira = ahora + datetime.timedelta(hours=12)
    tra = f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
  <header>
    <uniqueId>{int(ahora.timestamp())}</uniqueId>
    <generationTime>{ahora.strftime("%Y-%m-%dT%H:%M:%S")}</generationTime>
    <expirationTime>{expira.strftime("%Y-%m-%dT%H:%M:%S")}</expirationTime>
  </header>
  <service>{servicio}</service>
</loginTicketRequest>"""
    return tra.encode("utf-8")


def firmar_tra(tra_bytes, cert_path, key_path):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.serialization import pkcs7 as crypto_pkcs7
    from cryptography.x509 import load_pem_x509_certificate
    from cryptography.hazmat.backends import default_backend

    with open(key_path, "rb") as f:
        clave = serialization.load_pem_private_key(f.read(), password=None)

    with open(cert_path, "rb") as f:
        certificado = load_pem_x509_certificate(f.read(), default_backend())

    firmado = (
        crypto_pkcs7.PKCS7SignatureBuilder()
        .set_data(tra_bytes)
        .add_signer(certificado, clave, hashes.SHA256())
        .sign(serialization.Encoding.DER, [])
    )

    return base64.b64encode(firmado).decode("utf-8")

def obtener_token(cert_path, key_path, modo="produccion", servicio="wsfe", empresa=None):
    from ventas.models import TokenArca
    from requests import Session
    from zeep.transports import Transport
    from zeep import Client
    from datetime import timedelta

    if empresa:
        try:
            token_obj = TokenArca.objects.get(
                empresa=empresa,
                servicio=servicio,
                modo=modo
            )
            if token_obj.es_valido():
                return token_obj.token, token_obj.sign
        except TokenArca.DoesNotExist:
            pass

    url = WSAA_URL_HOMO if modo == "homologacion" else WSAA_URL_PROD

    tra = crear_tra(servicio)
    cms = firmar_tra(tra, cert_path, key_path)

    # 🔥 CONFIG SSL FIX
    session = Session()
    session.verify = False

    ctx = ssl.create_default_context()
    #ctx.set_ciphers('DEFAULT:@SECLEVEL=1')

    transport = Transport(session=session)
    client = Client(url, transport=transport)

    respuesta = client.service.loginCms(in0=cms)

    root = ET.fromstring(respuesta)
    token = root.find(".//token").text
    sign  = root.find(".//sign").text

    # Guardar token nuevo
    if empresa:
        expira = timezone.now() + timedelta(hours=12)

        TokenArca.objects.update_or_create(
            empresa=empresa,
            servicio=servicio,
            modo=modo,
            defaults={
                "token": token,
                "sign": sign,
                "expira": expira
            }
        )

    return token, sign