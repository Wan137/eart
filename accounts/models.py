from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class User(AbstractUser):
    ROLE_CHOICES = (('buyer','Buyer'), ('artist','Artist'), ('admin','Admin'))
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='buyer')

class ArtistProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="artist_profile",
    )
    display_name = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    def __str__(self):
        return self.display_name or self.user.username
