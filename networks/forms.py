# forms.py
from django import forms

class NetworkForm(forms.Form):
    OPCION_CHOICES = [
        ('opcion5G', 'Red 5G'),
        ('opcionGen', 'Red Genérica'),
    ]

    opciones = forms.ChoiceField(choices=OPCION_CHOICES, widget=forms.Select)
