from django import forms
from .models import Artwork

class ArtworkForm(forms.ModelForm):
    class Meta:
        model = Artwork
        fields = ["title", "slug", "description", "price", "categories", "file_preview", "file_original"]
        widgets = {
            "title":        forms.TextInput(attrs={"class": "form-control"}),
            "slug":         forms.TextInput(attrs={"class": "form-control"}),
            "description":  forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "price":        forms.NumberInput(attrs={"class": "form-control"}),
            "categories":   forms.SelectMultiple(attrs={"class": "form-select"}),
            "file_preview": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "file_original":forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

class CheckoutForm(forms.Form):
    full_name = forms.CharField(label="Full name", max_length=120,
                                widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(label="Email",
                             widget=forms.EmailInput(attrs={"class": "form-control"}))
    address = forms.CharField(label="Address", max_length=255,
                              widget=forms.TextInput(attrs={"class": "form-control"}))
