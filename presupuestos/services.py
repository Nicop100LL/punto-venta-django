from decimal import Decimal


def calcular_precio(empresa, producto, cantidad):
    cantidad = Decimal(str(cantidad))
    por_caja = empresa.usa_venta_por_caja and producto.venta_por_caja

    if (por_caja and producto.metros_cuadrados_por_caja and producto.precio_por_m2):
        return producto.metros_cuadrados_por_caja * producto.precio_por_m2, 'caja'

    if (not por_caja and producto.vende_por_bulto and producto.unidades_por_bulto
            and producto.precio_por_bulto and cantidad >= producto.unidades_por_bulto):
        return producto.precio_por_bulto / producto.unidades_por_bulto, 'bulto'

    if (producto.aplica_descuento and producto.cantidad_minima_descuento
            and cantidad >= producto.cantidad_minima_descuento
            and producto.precio_descuento_manual):
        return producto.precio_descuento_manual, 'descuento'

    return producto.precio_venta, None


def armar_item(empresa, producto, cantidad):
    cantidad = Decimal(str(cantidad))
    precio, tipo = calcular_precio(empresa, producto, cantidad)
    item = {
        'producto_id': producto.id,
        'nombre': producto.nombre,
        'cantidad': float(cantidad),
        'precio_unitario': float(precio),
        'subtotal': float(precio * cantidad),
        'tipo_precio': tipo,
        'venta_por_caja': tipo == 'caja',
    }
    if tipo == 'caja':
        item['metros_por_caja'] = float(producto.metros_cuadrados_por_caja)
        item['metros_totales'] = float(cantidad * producto.metros_cuadrados_por_caja)
        item['precio_m2'] = float(producto.precio_por_m2)
    return item