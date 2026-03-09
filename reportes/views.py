# reportes/views.py
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, F
from django.contrib.auth.decorators import login_required
import datetime
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from ventas.models import Venta, DetalleVenta
import math
from django.db.models import Sum, F
from decimal import Decimal

from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.contrib.auth.decorators import login_required
import datetime

from ventas.models import Venta, DetalleVenta

def convertir_a_bultos(cantidad):
    if cantidad <= 0:
        return 0
    if cantidad < 1:
        return 1
    return math.floor(cantidad)

@login_required
def reporte_diario(request):
    empresa = request.user.empresa

    # -----------------------------
    # 1) Fecha (GET ?fecha=YYYY-MM-DD) o hoy
    # -----------------------------
    fecha_str = request.GET.get('fecha')
    if fecha_str:
        try:
            fecha = datetime.date.fromisoformat(fecha_str)
        except Exception:
            fecha = timezone.localdate()
    else:
        fecha = timezone.localdate()

    # -----------------------------
    # 2) Ventas del día
    # -----------------------------
    ventas_qs = Venta.objects.filter(empresa=empresa, fecha__date=fecha)
    

    # -----------------------------
    # 3) Obtener todos los productos para el <select>
    # -----------------------------
    productos = DetalleVenta.objects.filter(
        venta__empresa=empresa
    ).values('producto__id', 'producto__nombre').distinct()

    # -----------------------------
    # 4) Filtrado por producto (GET ?producto=ID)
    # -----------------------------
    producto_id = request.GET.get('producto')
    detalles_qs = DetalleVenta.objects.filter(venta__in=ventas_qs)
    if producto_id:
        detalles_qs = detalles_qs.filter(producto_id=producto_id)

    # -----------------------------
    # 5) Totales generales
    # -----------------------------
    total_ventas = ventas_qs.aggregate(total=Sum('total'))['total'] or 0
    cantidad_ventas = ventas_qs.count()

    total_productos = detalles_qs.aggregate(total_cant=Sum('cantidad'))['total_cant'] or 0
    cantidad_tickets = ventas_qs.count()
    ticket_promedio = total_ventas / cantidad_tickets if cantidad_tickets > 0 else 0

    # -----------------------------
    # 6) Agregación por producto
    # -----------------------------
    detalles_con_subtotal = detalles_qs.annotate(
        subtotal=ExpressionWrapper(
            F('cantidad') * F('precio_unitario'),
            output_field=DecimalField()
        )
    )

    ventas = detalles_con_subtotal.values(
        'producto__id', 'producto__nombre'
    ).annotate(
        cantidad=Sum('cantidad'),
        total=Sum('subtotal')
    )
    
    # --------------------------------
    # Transformar cantidades en BULTOS
    # --------------------------------
    ventas = list(ventas)  # materializar antes de modificar

        
    for v in ventas:
        try:
            cantidad_val = float(v.get('cantidad', 0) or 0)
        except (TypeError, ValueError):
            cantidad_val = 0.0

        # Aplicar regla de bultos
        if cantidad_val <= 0:
            v['cantidad'] = 0
        elif cantidad_val < 1:
            v['cantidad'] = 1
        else:
            v['cantidad'] = math.floor(cantidad_val)

        # porcentaje sobre el total
        total_val = float(v.get('total', 0) or 0)
        v['porcentaje'] = (total_val / float(total_ventas or 1) * 100) if total_ventas > 0 else 0
        
    # Calcular total de bultos
    total_bultos = sum(v['cantidad'] for v in ventas)


    # Ordenamiento
    orden = request.GET.get("orden")
    if orden == "cantidad":
        ventas = sorted(ventas, key=lambda x: x['cantidad'], reverse=True)
    elif orden == "total":
        ventas = sorted(ventas, key=lambda x: x['total'], reverse=True)
    else:
        ventas = sorted(ventas, key=lambda x: x['producto__nombre'])

    # -----------------------------
    # 7) Totales por tipo de pago
    # -----------------------------
    totales_pago_qs = ventas_qs.values('tipo_pago').annotate(total=Sum('total'))
    TIPOS = dict(Venta.TIPO_PAGO_CHOICES)
    totales_pago = [
        {'tipo_pago': TIPOS.get(p['tipo_pago'], p['tipo_pago']), 'total': p['total'] or 0}
        for p in totales_pago_qs
    ]

    # -----------------------------
    # 8) Contexto para template
    # -----------------------------
    context = {
        'fecha': fecha.isoformat(),
        'ventas': ventas,
        'productos': productos,  # para el <select> de filtrado
        'total_ventas': total_ventas,
        'cantidad_ventas': cantidad_ventas,
        'totales_pago': totales_pago,
        'cantidad_tickets': cantidad_tickets,
        'ticket_promedio': ticket_promedio,
        'producto_filtrado': producto_id,  # para marcar la opción seleccionada
        'total_productos': total_bultos, 
    }

    return render(request, 'reportes/reporte_diario.html', context)


@login_required
def dashboard(request):
    empresa = request.user.empresa

    hoy = timezone.localdate()

    # Ventas de hoy
    ventas_qs = Venta.objects.filter(empresa=empresa, fecha__date=hoy)

    total_ventas = ventas_qs.aggregate(total=Sum('total'))['total'] or 0
    cantidad_tickets = ventas_qs.count()
    ticket_promedio = total_ventas / cantidad_tickets if cantidad_tickets > 0 else 0

    # Productos vendidos
    detalles_qs = DetalleVenta.objects.filter(venta__in=ventas_qs)

    ventas = (
        detalles_qs
        .values('producto__nombre')
        .annotate(cantidad=Sum('cantidad'))
        .order_by('-cantidad')[:5]
    )

    # Tipos de pago
    totales_pago = ventas_qs.values('tipo_pago').annotate(total=Sum('total'))

    context = {
        'hoy': hoy,
        'total_ventas': total_ventas,
        'ticket_promedio': ticket_promedio,
        'cantidad_tickets': cantidad_tickets,
        'top5': ventas,
        'totales_pago': totales_pago,
    }

    return render(request, 'reportes/dashboard.html', context)


@login_required
def reporte_mensual(request):
    import calendar
    from django.db.models import Count
    from django.db.models.functions import TruncDate

    empresa = request.user.empresa
    hoy = timezone.localdate()

    # Modo: semanal | mensual | rango
    modo = request.GET.get('modo', 'mensual')

    # Mes y año para modo mensual
    try:
        mes = int(request.GET.get('mes', hoy.month))
    except ValueError:
        mes = hoy.month
    try:
        anio = int(request.GET.get('anio', hoy.year))
    except ValueError:
        anio = hoy.year

    # Fechas libres para semanal y rango
    def parse_date(param, default):
        raw = request.GET.get(param)
        if raw:
            try:
                return datetime.date.fromisoformat(raw)
            except ValueError:
                pass
        return default

    fecha_inicio_raw = parse_date('fecha_inicio', None)
    fecha_fin_raw    = parse_date('fecha_fin', None)

    # Calcular rango según modo
    if modo == 'semanal':
        base         = fecha_inicio_raw or hoy
        fecha_inicio = base - datetime.timedelta(days=base.weekday())
        fecha_fin    = fecha_inicio + datetime.timedelta(days=6)
        label_periodo = f"Semana del {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}"

    elif modo == 'rango':
        fecha_inicio = fecha_inicio_raw or hoy.replace(day=1)
        fecha_fin    = fecha_fin_raw or hoy
        if fecha_inicio > fecha_fin:
            fecha_inicio, fecha_fin = fecha_fin, fecha_inicio
        label_periodo = f"{fecha_inicio.strftime('%d/%m/%Y')} → {fecha_fin.strftime('%d/%m/%Y')}"

    else:  # mensual
        fecha_inicio = datetime.date(anio, mes, 1)
        _, ultimo_dia = calendar.monthrange(anio, mes)
        fecha_fin     = datetime.date(anio, mes, ultimo_dia)
        label_periodo = f"{calendar.month_name[mes].capitalize()} {anio}"

    # QuerySets filtrados por rango
    ventas_qs   = Venta.objects.filter(empresa=empresa, fecha__date__gte=fecha_inicio, fecha__date__lte=fecha_fin)
    detalles_qs = DetalleVenta.objects.filter(venta__in=ventas_qs)

    # KPIs
    total_ventas     = ventas_qs.aggregate(t=Sum('total'))['t'] or 0
    cantidad_tickets = ventas_qs.count()
    ticket_promedio  = total_ventas / cantidad_tickets if cantidad_tickets else 0

    # Tabla de productos
    detalles_con_subtotal = detalles_qs.annotate(
        subtotal=ExpressionWrapper(F('cantidad') * F('precio_unitario'), output_field=DecimalField())
    )
    ventas_productos = list(
        detalles_con_subtotal
        .values('producto__id', 'producto__nombre')
        .annotate(cantidad=Sum('cantidad'), total=Sum('subtotal'))
    )

    for v in ventas_productos:
        try:
            cantidad_val = float(v.get('cantidad', 0) or 0)
        except (TypeError, ValueError):
            cantidad_val = 0.0
        if cantidad_val <= 0:
            v['cantidad'] = 0
        elif cantidad_val < 1:
            v['cantidad'] = 1
        else:
            v['cantidad'] = math.floor(cantidad_val)
        total_val = float(v.get('total', 0) or 0)
        v['porcentaje'] = (total_val / float(total_ventas or 1) * 100) if total_ventas else 0

    total_bultos = sum(v['cantidad'] for v in ventas_productos)

    orden = request.GET.get('orden', 'total')
    if orden == 'cantidad':
        ventas_productos.sort(key=lambda x: x['cantidad'], reverse=True)
    elif orden == 'producto':
        ventas_productos.sort(key=lambda x: x['producto__nombre'])
    else:
        ventas_productos.sort(key=lambda x: float(x['total'] or 0), reverse=True)

    # Totales por tipo de pago
    TIPOS = dict(Venta.TIPO_PAGO_CHOICES)
    totales_pago = [
        {'tipo_pago': TIPOS.get(p['tipo_pago'], p['tipo_pago']), 'total': p['total'] or 0}
        for p in ventas_qs.values('tipo_pago').annotate(total=Sum('total'))
    ]

    # Desglose día a día
    desglose_diario = list(
        ventas_qs
        .annotate(dia=TruncDate('fecha'))
        .values('dia')
        .annotate(tickets=Count('id'), total_dia=Sum('total'))
        .order_by('dia')
    )

    # Selectores del formulario
    primer_venta = Venta.objects.filter(empresa=empresa).order_by('fecha').first()
    primer_anio  = primer_venta.fecha.year if primer_venta else hoy.year
    anios_disponibles = list(range(primer_anio, hoy.year + 1))

    meses = [
        (1,'Enero'),(2,'Febrero'),(3,'Marzo'),(4,'Abril'),
        (5,'Mayo'),(6,'Junio'),(7,'Julio'),(8,'Agosto'),
        (9,'Septiembre'),(10,'Octubre'),(11,'Noviembre'),(12,'Diciembre'),
    ]

    context = {
        'modo': modo,
        'label_periodo': label_periodo,
        'fecha_inicio': fecha_inicio.isoformat(),
        'fecha_fin': fecha_fin.isoformat(),
        'mes': mes,
        'anio': anio,
        'anios_disponibles': anios_disponibles,
        'meses': meses,
        'total_ventas': total_ventas,
        'cantidad_tickets': cantidad_tickets,
        'ticket_promedio': ticket_promedio,
        'ventas': ventas_productos,
        'total_productos': total_bultos,
        'totales_pago': totales_pago,
        'desglose_diario': desglose_diario,
        'orden': orden,
    }
    return render(request, 'reportes/reporte_mensual.html', context)

@login_required
def ranking_productos(request):
    import calendar
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    from productos.models import Categoria

    empresa = request.user.empresa
    hoy = timezone.localdate()

    # ── Período (igual lógica que reporte_mensual) ──
    modo = request.GET.get('modo', 'mensual')

    try:
        mes = int(request.GET.get('mes', hoy.month))
    except ValueError:
        mes = hoy.month
    try:
        anio = int(request.GET.get('anio', hoy.year))
    except ValueError:
        anio = hoy.year

    def parse_date(param, default):
        raw = request.GET.get(param)
        if raw:
            try:
                return datetime.date.fromisoformat(raw)
            except ValueError:
                pass
        return default

    fecha_inicio_raw = parse_date('fecha_inicio', None)
    fecha_fin_raw    = parse_date('fecha_fin', None)

    if modo == 'semanal':
        base         = fecha_inicio_raw or hoy
        fecha_inicio = base - datetime.timedelta(days=base.weekday())
        fecha_fin    = fecha_inicio + datetime.timedelta(days=6)
        label_periodo = f"Semana del {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}"
    elif modo == 'rango':
        fecha_inicio = fecha_inicio_raw or hoy.replace(day=1)
        fecha_fin    = fecha_fin_raw or hoy
        if fecha_inicio > fecha_fin:
            fecha_inicio, fecha_fin = fecha_fin, fecha_inicio
        label_periodo = f"{fecha_inicio.strftime('%d/%m/%Y')} → {fecha_fin.strftime('%d/%m/%Y')}"
    else:  # mensual
        fecha_inicio = datetime.date(anio, mes, 1)
        _, ultimo_dia = calendar.monthrange(anio, mes)
        fecha_fin     = datetime.date(anio, mes, ultimo_dia)
        label_periodo = f"{calendar.month_name[mes].capitalize()} {anio}"

    # ── Filtros extra ──
    criterio          = request.GET.get('criterio', 'cantidad')   # 'cantidad' | 'monto'
    categoria_filtrada = request.GET.get('categoria', '')
    try:
        limite = int(request.GET.get('limite', 10))
    except ValueError:
        limite = 10

    # ── QuerySet base ──
    ventas_qs   = Venta.objects.filter(empresa=empresa, fecha__date__gte=fecha_inicio, fecha__date__lte=fecha_fin)
    detalles_qs = DetalleVenta.objects.filter(venta__in=ventas_qs)

    if categoria_filtrada:
        detalles_qs = detalles_qs.filter(producto__categoria_id=categoria_filtrada)

    # ── Agrupar por producto ──
    detalles_con_subtotal = detalles_qs.annotate(
        subtotal=ExpressionWrapper(
            F('cantidad') * F('precio_unitario'),
            output_field=DecimalField()
        )
    )

    productos_qs = list(
        detalles_con_subtotal
        .values('producto__id', 'producto__nombre', 'producto__categoria__nombre')
        .annotate(
            cantidad_raw=Sum('cantidad'),
            total=Sum('subtotal'),
        )
    )

    # ── Convertir a bultos ──
    for p in productos_qs:
        try:
            val = float(p['cantidad_raw'] or 0)
        except (TypeError, ValueError):
            val = 0.0
        if val <= 0:
            p['cantidad'] = 0
        elif val < 1:
            p['cantidad'] = 1
        else:
            p['cantidad'] = math.floor(val)
        p['nombre']    = p['producto__nombre']
        p['categoria'] = p['producto__categoria__nombre']

    # ── Ordenar por criterio ──
    if criterio == 'monto':
        productos_qs.sort(key=lambda x: float(x['total'] or 0), reverse=True)
        valor_primero = float(productos_qs[0]['total'] or 1) if productos_qs else 1
    else:
        productos_qs.sort(key=lambda x: x['cantidad'], reverse=True)
        valor_primero = productos_qs[0]['cantidad'] if productos_qs else 1

    # ── Totales globales (para porcentaje) ──
    total_ventas   = sum(float(p['total'] or 0) for p in productos_qs)
    total_cantidad = sum(p['cantidad'] for p in productos_qs)

    # ── Calcular porcentaje y barra ──
    for p in productos_qs:
        total_val = float(p['total'] or 0)
        p['porcentaje'] = (total_val / total_ventas * 100) if total_ventas else 0

        # barra_pct: proporcional al valor del 1er puesto (siempre 100%)
        if criterio == 'monto':
            p['barra_pct'] = round((total_val / valor_primero * 100), 1) if valor_primero else 0
        else:
            p['barra_pct'] = round((p['cantidad'] / valor_primero * 100), 1) if valor_primero else 0

    # ── Aplicar límite ──
    ranking = productos_qs[:limite] if limite > 0 else productos_qs

    # ── Selectores del formulario ──
    categorias = Categoria.objects.filter(empresa=empresa).order_by('nombre')
    primer_venta = Venta.objects.filter(empresa=empresa).order_by('fecha').first()
    primer_anio  = primer_venta.fecha.year if primer_venta else hoy.year
    anios_disponibles = list(range(primer_anio, hoy.year + 1))
    meses = [
        (1,'Enero'),(2,'Febrero'),(3,'Marzo'),(4,'Abril'),
        (5,'Mayo'),(6,'Junio'),(7,'Julio'),(8,'Agosto'),
        (9,'Septiembre'),(10,'Octubre'),(11,'Noviembre'),(12,'Diciembre'),
    ]

    context = {
        'modo': modo,
        'label_periodo': label_periodo,
        'fecha_inicio': fecha_inicio.isoformat(),
        'fecha_fin': fecha_fin.isoformat(),
        'mes': mes,
        'anio': anio,
        'anios_disponibles': anios_disponibles,
        'meses': meses,
        'criterio': criterio,
        'limite': limite,
        'categorias': categorias,
        'categoria_filtrada': categoria_filtrada,
        'ranking': ranking,
        'total_ventas': total_ventas,
        'total_cantidad': total_cantidad,
    }
    return render(request, 'reportes/ranking_productos.html', context)

@login_required
def analytics(request):
    """
    Página de analytics con:
    - Comparativas: hoy vs ayer, semana, mes, año, o rango libre (4 date pickers)
    - Gráfico de evolución: barras agrupadas (actual vs anterior)
    - Gráfico tipo de pago: dona o barras
    - Top 5 productos: barras horizontales o torta
    """
    import calendar as cal
    import json
    from django.db.models.functions import TruncDate
    from django.db.models import Count

    empresa = request.user.empresa
    hoy     = timezone.localdate()

    comparativa = request.GET.get('comparativa', 'mes')
    # Opciones: 'dia' | 'semana' | 'mes' | 'anio' | 'rango'

    # ── Helper: suma total de ventas en un rango ─────────────────────
    def ventas_total(desde, hasta):
        return Venta.objects.filter(
            empresa=empresa,
            fecha__date__gte=desde,
            fecha__date__lte=hasta,
        ).aggregate(t=Sum('total'))['t'] or 0

    def tickets_count(desde, hasta):
        return Venta.objects.filter(
            empresa=empresa,
            fecha__date__gte=desde,
            fecha__date__lte=hasta,
        ).count()

    # ── Helper: parsear fecha GET ────────────────────────────────────
    def parse_date(param, default):
        raw = request.GET.get(param)
        if raw:
            try:
                return datetime.date.fromisoformat(raw)
            except ValueError:
                pass
        return default

    # ── Calcular los dos períodos según modo ─────────────────────────
    if comparativa == 'dia':
        actual_desde   = hoy
        actual_hasta   = hoy
        anterior_desde = hoy - datetime.timedelta(days=1)
        anterior_hasta = hoy - datetime.timedelta(days=1)
        label_actual   = f"Hoy ({hoy.strftime('%d/%m')})"
        label_anterior = f"Ayer ({anterior_desde.strftime('%d/%m')})"

    elif comparativa == 'semana':
        actual_desde   = hoy - datetime.timedelta(days=hoy.weekday())
        actual_hasta   = hoy
        anterior_desde = actual_desde - datetime.timedelta(days=7)
        anterior_hasta = actual_hasta - datetime.timedelta(days=7)
        label_actual   = "Esta semana"
        label_anterior = "Semana anterior"

    elif comparativa == 'anio':
        actual_desde   = datetime.date(hoy.year, 1, 1)
        actual_hasta   = hoy
        anterior_desde = datetime.date(hoy.year - 1, 1, 1)
        anterior_hasta = datetime.date(hoy.year - 1, hoy.month, hoy.day)
        label_actual   = f"Este año ({hoy.year})"
        label_anterior = f"Año anterior ({hoy.year - 1})"

    elif comparativa == 'rango':
        # Período A: el que el usuario quiere analizar
        actual_desde   = parse_date('a_desde', hoy.replace(day=1))
        actual_hasta   = parse_date('a_hasta', hoy)
        # Período B: el que el usuario quiere comparar
        anterior_desde = parse_date('b_desde', hoy.replace(day=1) - datetime.timedelta(days=1))
        anterior_hasta = parse_date('b_hasta', hoy - datetime.timedelta(days=hoy.day))
        # Corregir si vienen invertidos
        if actual_desde > actual_hasta:
            actual_desde, actual_hasta = actual_hasta, actual_desde
        if anterior_desde > anterior_hasta:
            anterior_desde, anterior_hasta = anterior_hasta, anterior_desde
        label_actual   = f"{actual_desde.strftime('%d/%m/%Y')} → {actual_hasta.strftime('%d/%m/%Y')}"
        label_anterior = f"{anterior_desde.strftime('%d/%m/%Y')} → {anterior_hasta.strftime('%d/%m/%Y')}"

    else:  # mes (default)
        actual_desde = hoy.replace(day=1)
        actual_hasta = hoy
        if hoy.month == 1:
            anterior_desde = datetime.date(hoy.year - 1, 12, 1)
            max_dia = cal.monthrange(hoy.year - 1, 12)[1]
            anterior_hasta = datetime.date(hoy.year - 1, 12, min(hoy.day, max_dia))
        else:
            anterior_desde = datetime.date(hoy.year, hoy.month - 1, 1)
            max_dia = cal.monthrange(hoy.year, hoy.month - 1)[1]
            anterior_hasta = datetime.date(hoy.year, hoy.month - 1, min(hoy.day, max_dia))
        label_actual   = "Este mes"
        label_anterior = "Mes anterior"

    # ── KPIs ─────────────────────────────────────────────────────────
    ventas_actual    = ventas_total(actual_desde, actual_hasta)
    ventas_anterior  = ventas_total(anterior_desde, anterior_hasta)
    tickets_actual   = tickets_count(actual_desde, actual_hasta)
    tickets_anterior = tickets_count(anterior_desde, anterior_hasta)

    ticket_promedio_actual   = float(ventas_actual)  / tickets_actual   if tickets_actual   else 0
    ticket_promedio_anterior = float(ventas_anterior) / tickets_anterior if tickets_anterior else 0

    def variacion(actual, anterior):
        if not anterior:
            return None
        return round((float(actual) - float(anterior)) / float(anterior) * 100, 1)

    var_ventas  = variacion(ventas_actual,  ventas_anterior)
    var_tickets = variacion(tickets_actual, tickets_anterior)
    var_ticket  = variacion(ticket_promedio_actual, ticket_promedio_anterior)

    # ── Gráfico 1: Evolución día a día — barras agrupadas ────────────
    def evolucion_por_dia(desde, hasta):
        return {
            str(r['dia']): float(r['total_dia'])
            for r in Venta.objects.filter(
                empresa=empresa,
                fecha__date__gte=desde,
                fecha__date__lte=hasta,
            )
            .annotate(dia=TruncDate('fecha'))
            .values('dia')
            .annotate(total_dia=Sum('total'))
            .order_by('dia')
        }

    evol_actual   = evolucion_por_dia(actual_desde, actual_hasta)
    evol_anterior = evolucion_por_dia(anterior_desde, anterior_hasta)

    # Unión de todas las fechas para los labels del eje X
    todas_fechas = sorted(set(list(evol_actual.keys()) + list(evol_anterior.keys())))
    labels_evolucion      = todas_fechas
    datos_actual_linea    = [evol_actual.get(f, 0)   for f in todas_fechas]
    datos_anterior_linea  = [evol_anterior.get(f, 0) for f in todas_fechas]

    # ── Gráfico 2: Tipo de pago ──────────────────────────────────────
    TIPOS = dict(Venta.TIPO_PAGO_CHOICES)
    pagos_qs = list(
        Venta.objects.filter(
            empresa=empresa,
            fecha__date__gte=actual_desde,
            fecha__date__lte=actual_hasta,
        )
        .values('tipo_pago')
        .annotate(total=Sum('total'))
        .order_by('-total')
    )
    labels_pagos = [TIPOS.get(p['tipo_pago'], p['tipo_pago']) for p in pagos_qs]
    datos_pagos  = [float(p['total']) for p in pagos_qs]

    # ── Gráfico 3: Top 5 productos (por monto, período actual) ───────
    top5_qs = list(
        DetalleVenta.objects
        .filter(
            venta__empresa=empresa,
            venta__fecha__date__gte=actual_desde,
            venta__fecha__date__lte=actual_hasta,
        )
        .annotate(
            subtotal=ExpressionWrapper(
                F('cantidad') * F('precio_unitario'),
                output_field=DecimalField()
            )
        )
        .values('producto__nombre')
        .annotate(total=Sum('subtotal'))
        .order_by('-total')[:5]
    )
    labels_top5 = [p['producto__nombre'] for p in top5_qs]
    datos_top5  = [float(p['total']) for p in top5_qs]

    context = {
        # Modo activo
        'comparativa':    comparativa,
        'label_actual':   label_actual,
        'label_anterior': label_anterior,

        # Fechas para repoblar los pickers en el template
        'actual_desde':   actual_desde.isoformat(),
        'actual_hasta':   actual_hasta.isoformat(),
        'anterior_desde': anterior_desde.isoformat(),
        'anterior_hasta': anterior_hasta.isoformat(),

        # KPIs
        'ventas_actual':             ventas_actual,
        'ventas_anterior':           ventas_anterior,
        'tickets_actual':            tickets_actual,
        'tickets_anterior':          tickets_anterior,
        'ticket_promedio_actual':    ticket_promedio_actual,
        'ticket_promedio_anterior':  ticket_promedio_anterior,
        'var_ventas':                var_ventas,
        'var_tickets':               var_tickets,
        'var_ticket':                var_ticket,

        # Datos Chart.js (JSON)
        'labels_evolucion':      json.dumps(labels_evolucion),
        'datos_actual_linea':    json.dumps(datos_actual_linea),
        'datos_anterior_linea':  json.dumps(datos_anterior_linea),
        'labels_pagos':          json.dumps(labels_pagos),
        'datos_pagos':           json.dumps(datos_pagos),
        'labels_top5':           json.dumps(labels_top5),
        'datos_top5':            json.dumps(datos_top5),
        'label_actual_json':     json.dumps(label_actual),
        'label_anterior_json':   json.dumps(label_anterior),

        # Opciones del selector
        'comparativas_opciones': [
            ('dia',    'Hoy vs ayer'),
            ('semana', 'Esta semana vs anterior'),
            ('mes',    'Este mes vs anterior'),
            ('anio',   'Este año vs anterior'),
            ('rango',  'Rango libre'),
        ],
    }
    return render(request, 'reportes/analytics.html', context)