from django.db import models
from usuarios.models import Empresa

class ModeloImpresion(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="modelos_impresion"
    )

    nombre = models.CharField(max_length=100)

    # ===== HOJA =====
    tamano_hoja = models.CharField(
        max_length=10,
        choices=[('A4', 'A4'), ('A5', 'A5')],
        default='A4'
    )

    orientacion = models.CharField(
        max_length=10,
        choices=[('portrait', 'Vertical'), ('landscape', 'Horizontal')],
        default='portrait'
    )

    columnas = models.PositiveIntegerField(default=1)
    filas = models.PositiveIntegerField(default=1)

    # ===== ALINEACIÓN =====
    alineacion_horizontal = models.CharField(
        max_length=20,
        choices=[
            ('flex-start', 'Izquierda'),
            ('center', 'Centro'),
            ('flex-end', 'Derecha'),
        ],
        default='center'
    )

    alineacion_vertical = models.CharField(
        max_length=20,
        choices=[
            ('flex-start', 'Arriba'),
            ('center', 'Centro'),
            ('flex-end', 'Abajo'),
            ('space-between', 'Distribuido'),
        ],
        default='center'
    )

    # ===== VISUAL GENERAL =====
    fondo_color = models.CharField(max_length=20, default="#FFFFFF")
    borde_color = models.CharField(max_length=20, default="#000000")
    padding = models.PositiveIntegerField(default=5)

    # ===== TÍTULO =====
    titulo_color = models.CharField(max_length=20, default="#000000")
    titulo_tamano = models.PositiveIntegerField(default=14)
    titulo_negrita = models.BooleanField(default=True)

    # ===== PRECIO =====
    precio_color = models.CharField(max_length=20, default="#000000")
    precio_tamano = models.PositiveIntegerField(default=28)
    precio_negrita = models.BooleanField(default=True)
    
    # ===== CÓDIGO DE BARRAS =====
    mostrar_barcode = models.BooleanField(default=False)

    barcode_ancho = models.PositiveIntegerField(
        default=120,
        help_text="Ancho del código de barras en px"
    )

    barcode_alto = models.PositiveIntegerField(
        default=40,
        help_text="Alto del código de barras en px"
    )

    barcode_mostrar_texto = models.BooleanField(
        default=False,
        help_text="Mostrar el código debajo del barcode"
    )


    # ===== OPCIONES =====
    mostrar_codigo = models.BooleanField(default=True)
    mostrar_precio = models.BooleanField(default=True)

    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.empresa})"



class ModeloEtiqueta(models.Model):
    """
    Modelo de configuración para imprimir etiquetas de productos.
    Permite etiquetas de 58mm o 80mm de ancho, con alto fijo o dinámico.
    Compatible con impresión vía microservicio o PDF.
    """

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="modelos_etiquetas"
    )

    nombre = models.CharField(max_length=100, help_text="Nombre del modelo de etiqueta")

    # ===== TAMAÑO DE LA ETIQUETA =====
    ANCHOS_POSIBLES = [
        (58, "58mm"),
        (80, "80mm"),
    ]
    ancho_mm = models.PositiveIntegerField(
        choices=ANCHOS_POSIBLES,
        default=58,
        help_text="Ancho de la etiqueta en mm"
    )

    alto_mm = models.PositiveIntegerField(
        default=0,
        help_text="0 = alto automático según contenido"
    )


    # ===== MÁRGENES =====
    margen_superior = models.PositiveIntegerField(default=2, help_text="Márgen superior en mm")
    margen_inferior = models.PositiveIntegerField(default=2, help_text="Márgen inferior en mm")
    margen_izquierdo = models.PositiveIntegerField(default=2, help_text="Márgen izquierdo en mm")
    margen_derecho = models.PositiveIntegerField(default=2, help_text="Márgen derecho en mm")

    # ===== VISUAL =====
    fondo_color = models.CharField(max_length=20, default="#FFFFFF", help_text="Color de fondo de la etiqueta")
    borde_color = models.CharField(max_length=20, default="#000000", help_text="Color del borde de la etiqueta")
    padding = models.PositiveIntegerField(default=2, help_text="Padding interno de la etiqueta en px")

    # ===== TEXTO =====
    mostrar_nombre = models.BooleanField(default=True, help_text="Mostrar nombre del producto")
    nombre_tamano = models.PositiveIntegerField(default=10, help_text="Tamaño del texto del nombre en px")
    nombre_negrita = models.BooleanField(default=True, help_text="Nombre en negrita")

    mostrar_precio = models.BooleanField(default=True, help_text="Mostrar precio del producto")
    precio_tamano = models.PositiveIntegerField(default=12, help_text="Tamaño del texto del precio en px")
    precio_negrita = models.BooleanField(default=True, help_text="Precio en negrita")

    # ===== CÓDIGO DE BARRAS =====
    mostrar_barcode = models.BooleanField(default=False, help_text="Incluir código de barras en la etiqueta")
    barcode_ancho = models.PositiveIntegerField(default=120, help_text="Ancho del código de barras en px")
    barcode_alto = models.PositiveIntegerField(default=40, help_text="Alto del código de barras en px")
    barcode_mostrar_texto = models.BooleanField(default=False, help_text="Mostrar el código debajo del barcode")

    # ===== OPCIONES DE IMPRESIÓN =====
    usar_microservicio = models.BooleanField(
        default=True,
        help_text="Si la impresora es USB, usar microservicio para impresión automática"
    )

    activo = models.BooleanField(default=True, help_text="Si el modelo está activo y disponible")

    def __str__(self):
        return f"{self.nombre} ({self.empresa})"
