
"""Decodificación de códigos de barras de etiquetas/tickets de balanza.
Sin dependencias de Django.
"""

import re

FORMATO_RE = re.compile(r'^[0-9PIBCSA]{12}$')


def digito_verificador(cuerpo12):
    s = sum(
        int(c) * (3 if i % 2 else 1)
        for i, c in enumerate(cuerpo12)
    )
    return (10 - s % 10) % 10


def ean13_valido(codigo):
    return (
        len(codigo) == 13
        and codigo.isdigit()
        and digito_verificador(codigo[:12]) == int(codigo[12])
    )


def parsear_etiqueta(formato, codigo):
    """Devuelve (plu, importe_entero) para formatos antiguos con I."""
    if not FORMATO_RE.fullmatch(formato or ''):
        return None

    if not ean13_valido(codigo or ''):
        return None

    plu = ''
    importe = ''

    for f, c in zip(formato, codigo[:12]):
        if f.isdigit():
            if f != c:
                return None
        elif f == 'P':
            plu += c
        elif f == 'I':
            importe += c

    if not plu or not importe or int(plu) < 1:
        return None

    return int(plu), int(importe)


def parsear_peso(formato, codigo):
    """Devuelve (plu, peso_gramos) para etiquetas configuradas por peso.

    Ejemplo de formato: 20PPPPIIIIII.
    En este modo, los seis dígitos variables representan gramos.
    """
    if not FORMATO_RE.fullmatch(formato or ''):
        return None

    if not ean13_valido(codigo or ''):
        return None

    plu = ''
    peso = ''

    for f, c in zip(formato, codigo[:12]):
        if f.isdigit():
            if f != c:
                return None
        elif f == 'P':
            plu += c
        elif f == 'I':
            peso += c

    if not plu or not peso or int(plu) < 1:
        return None

    peso_gramos = int(peso)

    if peso_gramos <= 0:
        return None

    return int(plu), peso_gramos