from django import forms
from .models import Venta, DetalleVenta
from productos.models import Producto
from .models import Cliente

class DetalleVentaForm(forms.Form):
    producto = forms.ModelChoiceField(queryset=Producto.objects.all())
    cantidad = forms.IntegerField(min_value=1)

class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['cliente']

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        exclude = ['empresa']
        fields = '__all__'