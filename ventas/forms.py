from django import forms
from .models import Venta, DetalleVenta
from productos.models import Producto
from .models import Cliente
from .models import EgresoCaja

class DetalleVentaForm(forms.Form):
    producto = forms.ModelChoiceField(queryset=Producto.objects.all())
    cantidad = forms.IntegerField(min_value=1)

class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['cliente', 'nota']

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        exclude = ['empresa']
        fields = '__all__'
        


class EgresoForm(forms.ModelForm):
    class Meta:
        model = EgresoCaja
        fields = ['tipo', 'concepto', 'monto', 'metodo_pago', 'proveedor', 'comprobante', 'observaciones']
        widgets = {
            'concepto': forms.TextInput(attrs={
                'class': 'w-full border rounded px-3 py-2',
                'placeholder': 'Ej: Pago luz enero 2026'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'w-full border rounded px-3 py-2',
                'step': '0.01'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'w-full border rounded px-3 py-2',
                'rows': 3
            }),
        }        