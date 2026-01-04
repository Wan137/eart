from django.db import models
from django.conf import settings

class Order(models.Model):
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    email = models.EmailField()
    full_name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    total_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    status = models.CharField(
    max_length=20,
    choices=[("pending","Pending"),("paid","Paid"),("failed","Failed")],
    default="pending",
)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    artwork = models.ForeignKey("catalog.Artwork", on_delete=models.PROTECT)
    unit_price = models.DecimalField(max_digits=9, decimal_places=2)
    qty = models.PositiveIntegerField(default=1)

