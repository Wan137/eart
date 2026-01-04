from django import forms
from .models import Artwork
from django.contrib.auth.models import User
from accounts.models import ArtistProfile
from .models import Review

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
    

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class ArtistProfileForm(forms.ModelForm):
    class Meta:
        model = ArtistProfile
        fields = ['display_name', 'bio', 'profile_image']

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control bg-dark text-white border-secondary', 'rows': 3, 'placeholder': 'Write your opinion...'}),
            'rating': forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary', 'style': 'width: auto;'}),
        }