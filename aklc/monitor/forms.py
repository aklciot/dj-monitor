from django import forms

class ContactForm(forms.Form):
    descr = forms.CharField(widget=forms.Textarea)
    