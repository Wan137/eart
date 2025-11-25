from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from accounts.models import ArtistProfile  # если ArtistProfile в другом месте — поправь импорт

User = get_user_model()

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    ROLE_CHOICES = (
        ("buyer", "Buyer"),
        ("artist", "Artist"),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial="buyer")
    display_name = forms.CharField(required=False, help_text="For artists (public name)")

    class Meta:
        model = User
        fields = ("username", "email", "role", "display_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
            # создаём профиль для художника
            if user.role == "artist":
                ArtistProfile.objects.get_or_create(
                    user=user,
                    defaults={"display_name": self.cleaned_data.get("display_name") or user.username},
                )
        return user
