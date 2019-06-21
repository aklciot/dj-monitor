from django import forms
from .models import Node

class ContactForm(forms.Form):
    descr = forms.CharField(widget=forms.Textarea)


class NodeDetailForm(forms.ModelForm):
    class Meta:
        model = Node
        fields = ['descr', 'allowedDowntime', 'hardware', 'software', 'battName', 'battWarn', 'battCritical']
        widgets = {
            'descr': forms.Textarea(attrs={'rows': 3}),
        }

class NodeNotifyForm(forms.Form):
    NOTIFY_ME = [
        ('Y', 'Notify me'),
        ('N', 'No notifications, thanks'),
    ]
    email = forms.BooleanField(required=False)
    sms = forms.BooleanField(required=False)
    notification = forms.ChoiceField(choices=NOTIFY_ME)