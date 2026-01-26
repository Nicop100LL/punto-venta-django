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
