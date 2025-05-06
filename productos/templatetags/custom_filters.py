from django import template
from django.utils.formats import number_format

register = template.Library()

@register.filter
def formato_precio(value):
    if value is None:
        return ''
    # Convierte el número en un formato con punto como separador de miles y coma como decimales
    return number_format(value, force_grouping=True).replace(',', '.')

@register.filter
def to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0
