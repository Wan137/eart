from django.db import models
from django.utils import timezone
import uuid

class DownloadToken(models.Model):
    order_item = models.OneToOneField("orders.OrderItem", on_delete=models.CASCADE, related_name="download")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField()
    remaining = models.PositiveIntegerField(default=3)

    def is_valid(self):
        return self.remaining > 0 and timezone.now() < self.expires_at
    
    def __str__(self):
        return str(self.token)
    

class DownloadLog(models.Model):
    token = models.ForeignKey(DownloadToken, on_delete=models.CASCADE, related_name="logs")
    when = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)