def empresa_context(request):
    """
    Agrega 'empresa' al contexto de todos los templates si el usuario está autenticado.
    """
    empresa = None
    if request.user.is_authenticated and hasattr(request.user, 'empresa'):
        empresa = request.user.empresa
    return {'empresa': empresa}
