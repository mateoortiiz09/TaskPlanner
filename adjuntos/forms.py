from django import forms


class AdjuntoForm(forms.Form):
    archivo = forms.FileField()
