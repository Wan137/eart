from django.contrib import admin
from .models import Artwork, Category


@admin.register(Artwork)
class ArtworkAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "price", "is_active", "created_at")
    list_filter = ("is_active", "categories", "created_at")
    search_fields = ("title", "artist__display_name", "artist__user__username")
    ordering = ("-created_at",)

    actions = ("approve_selected", "reject_selected")

    @admin.action(description="Approve selected artworks (publish)")
    def approve_selected(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Published {updated} artwork(s).")

    @admin.action(description="Reject selected artworks (hide)")
    def reject_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Hidden {updated} artwork(s).")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    ordering = ("name",)

