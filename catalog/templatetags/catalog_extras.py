from django import template
from catalog.models import Favorite

register = template.Library()

@register.filter
def has_liked(user, artwork):
    if not user.is_authenticated:
        return False
    return Favorite.objects.filter(user=user, artwork=artwork).exists()