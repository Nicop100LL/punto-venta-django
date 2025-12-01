from django import template

register = template.Library()

@register.filter
def formato_precio(value):
    if value is None:
        return ''

    try:
        value = float(value)
    except:
        return value

    # Si el número es entero -> se formatea sin decimales
    if value.is_integer():
        return f"{int(value):,}".replace(",", ".")

    # Si tiene decimales -> mantenerlos
    valor_str = f"{value}"
    entero, decimal = valor_str.split(".")

    # Formatear miles
    entero = f"{int(entero):,}".replace(",", ".")

    # Quitar ceros extra al final de los decimales (opcional)
    decimal = decimal.rstrip("0")

    return f"{entero},{decimal}"


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
