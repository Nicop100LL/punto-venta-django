from django import template

from ..models import Balanza

register = template.Library()


@register.simple_tag(takes_context=True)
def formatos_etiqueta(context):
    """Formatos de etiqueta de las balanzas de la empresa (vacío si no usa balanza)."""
    request = context.get('request')
    empresa = getattr(getattr(request, 'user', None), 'empresa', None)
    if not empresa or not empresa.usa_balanza:
        return []
    return sorted(set(Balanza.objects.filter(empresa=empresa, activa=True)
                      .exclude(formato_etiqueta='')
                      .values_list('formato_etiqueta', flat=True)))
