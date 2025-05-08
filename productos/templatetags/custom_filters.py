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
    
@register.filter
def calcular_descuento(precio_unitario, precio_venta):
    if precio_venta > 0 and precio_unitario < precio_venta:
        return round((1 - (precio_unitario / precio_venta)) * 100, 0)
    return 0
