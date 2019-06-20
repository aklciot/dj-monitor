from django import forms
from .models import Node

class ContactForm(forms.Form):
    descr = forms.CharField(widget=forms.Textarea)


class NodeDetailForm(forms.ModelForm):
    class Meta:
        model = Node
        fields = ['descr', 'allowedDowntime', 'hardware', 'software', 'battName']
        widgets = {
            'descr': forms.Textarea(attrs={'rows': 3}),
        }