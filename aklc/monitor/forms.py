from django import forms
from .models import Node, MessageType, MessageItem

class ContactForm(forms.Form):
    descr = forms.CharField(widget=forms.Textarea)


class NodeDetailForm(forms.ModelForm):
    class Meta:
        model = Node
        fields = ['descr', 'allowedDowntime', 'hardware', 'software', 'battName', 'battWarn', 'battCritical', 'portal', 'team', 'latitude', 'longitude']
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

class MessageTypeDetailForm(forms.ModelForm):
    class Meta:
        model = MessageType
        fields = ['msgName', 'descr']
        widgets = {
            'descr': forms.Textarea(attrs={'rows': 1}),
        }

class MessageItemDetailForm(forms.ModelForm):
    class Meta:
        model = MessageItem
        fields = ['order', 'name', 'isTag', 'fieldType',  ]
        widgets = {
            'fieldType': forms.TextInput(attrs={'size': 1}),
        }

class NodeMessageForm(forms.ModelForm):
    class Meta:
        model = Node
        fields = ['messagetype', 'thingsboardUpload', 'thingsboardCred', 'locationOverride', 'projectOverride']
        #widgets = {
        #    'thingsboardCred': forms.Textarea(attrs={'rows': 3}),
        #}

