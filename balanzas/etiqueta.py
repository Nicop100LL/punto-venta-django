"""Decodificación del código de barras de las etiquetas/tickets de la balanza.
Sin dependencias de Django (se puede probar solo)."""
import re

FORMATO_RE = re.compile(r'^[0-9PIBCSA]{12}$')


def digito_verificador(cuerpo12):
    s = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(cuerpo12))
    return (10 - s % 10) % 10


def ean13_valido(codigo):
    return (len(codigo) == 13 and codigo.isdigit()
            and digito_verificador(codigo[:12]) == int(codigo[12]))


def parsear_etiqueta(formato, codigo):
    """Devuelve (plu, importe_entero) o None si el código no corresponde al formato.
    formato: 12 caracteres. Dígitos = fijos, P = PLU, I = importe (B, C, S, A se ignoran)."""
    if not FORMATO_RE.match(formato or '') or not ean13_valido(codigo or ''):
        return None
    plu = imp = ''
    for f, c in zip(formato, codigo[:12]):
        if f.isdigit():
            if f != c:
                return None
        elif f == 'P':
            plu += c
        elif f == 'I':
            imp += c
    if not plu or not imp or int(plu) < 1:
        return None
    return int(plu), int(imp)
