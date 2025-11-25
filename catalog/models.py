from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from accounts.models import ArtistProfile

class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class Artwork(models.Model):
    artist = models.ForeignKey(ArtistProfile, on_delete=models.CASCADE, related_name="artworks")
    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    categories = models.ManyToManyField(Category, blank=True)
    tags = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    file_original = models.FileField(upload_to="art/original/")
    file_preview = models.ImageField(upload_to="art/preview/", blank=True)
    is_active = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:40]
            self.slug = base if base else f"art-{self.pk or ''}"
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse("web_artwork_detail", args=[self.slug])
