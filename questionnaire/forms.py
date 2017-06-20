from django import forms
from .models import Questionnaire

class NewLandingForm(forms.Form):
    label = forms.CharField(max_length=64, required=True)
    questionnaire = forms.ModelChoiceField(
        Questionnaire.objects.all(),
        widget=forms.widgets.RadioSelect(),
        empty_label=None,
        required=True,
    )

