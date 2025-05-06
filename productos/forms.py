from django import forms
from .models import Producto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        exclude = ['empresa']  # No se muestra en el formulario, la asignamos desde la vista
