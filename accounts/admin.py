from django.contrib import admin
from .models import ArtistProfile, User

admin.site.register(User)

@admin.register(ArtistProfile)
class ArtistProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user")
    search_fields = ("display_name", "user__username", "user__email")

# Register your models here.
