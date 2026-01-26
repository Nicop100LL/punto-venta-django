from .models import CierreCaja



def get_caja_abierta(usuario, empresa):
    """
    Devuelve la caja abierta si el usuario necesita caja
    """
    if usuario.is_superuser_or_staff():
        return None

    return CierreCaja.objects.filter(
        usuario=usuario,
        empresa=empresa,
        estado='abierta'
    ).first()


def usuario_necesita_caja(usuario):
    """
    Devuelve True si el usuario debe operar con caja
    """
    return not usuario.is_superuser_or_staff()
