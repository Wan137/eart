from rest_framework import serializers
from .models import Order, OrderItem
from catalog.serializers import ArtworkListSerializer
from downloads.models import DownloadToken
from django.urls import reverse

class OrderItemSerializer(serializers.ModelSerializer):
    artwork = ArtworkListSerializer(read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ("id","artwork","unit_price","qty", "download_url")

    def get_download_url(self, obj):
        try:
            token = obj.download.token
        except DownloadToken.DoesNotExist:
            return None
        request = self.context.get("request")
        url = reverse("download", args=[str(token)])
        return request.build_absolute_uri(url) if request else url

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = ("id","email","full_name","paid","total_amount","created_at","items")
