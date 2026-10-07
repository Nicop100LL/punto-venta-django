from django import forms

from .models import AgenteBalanza, Balanza

CLS = 'w-full px-3 py-2 border border-gray-300 rounded-lg'


class BalanzaForm(forms.ModelForm):
    class Meta:
        model = Balanza
        fields = ['nombre', 'agente', 'direccion_equipo', 'tipo_conexion', 'ip', 'puerto',
                  'puerto_com', 'decimales_precio', 'sector_por_defecto', 'formato_etiqueta',
                  'activa']

    def __init__(self, *args, empresa, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        self.fields['agente'].queryset = AgenteBalanza.objects.filter(empresa=empresa)
        self.fields['agente'].required = False
        for n, f in self.fields.items():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs['class'] = CLS

    def clean_formato_etiqueta(self):
        f = (self.cleaned_data.get('formato_etiqueta') or '').upper()
        if 'P' not in f or 'I' not in f:
            raise forms.ValidationError('Debe incluir al menos una P (PLU) y una I (importe).')
        return f

    def clean(self):
        d = super().clean()
        if d.get('tipo_conexion') == 'red' and not d.get('ip'):
            self.add_error('ip', 'Indicá la IP fija de la balanza.')
        if d.get('tipo_conexion') == 'usb' and not d.get('puerto_com'):
            self.add_error('puerto_com', 'Indicá el puerto COM (ej: COM3).')
        return d

    def save(self, commit=True):
        b = super().save(commit=False)
        b.empresa = self.empresa
        if not b.agente_id:
            agentes = list(AgenteBalanza.objects.filter(empresa=self.empresa)[:2])
            if len(agentes) == 1:
                b.agente = agentes[0]
        if commit:
            b.save()
        return b
