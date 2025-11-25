from django.contrib import admin
from .models import DownloadToken


@admin.register(DownloadToken)
class DownloadTokenAdmin(admin.ModelAdmin):
    list_display = ("token","order_item","expires_at","remaining")
    search_fields = ("token",)
