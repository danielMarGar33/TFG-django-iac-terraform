# forms.py
from django import forms

class NetworkForm(forms.Form):
    OPCION_CHOICES = [
        ('opcion5G_open', 'Red open5G'),
        ('opcion5G_free', 'Red free5G'),
        ('opcionGen', 'Red Ampliada de Pruebas'),
    ]

    opciones = forms.ChoiceField(choices=OPCION_CHOICES, widget=forms.Select)
