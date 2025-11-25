from rest_framework import serializers
from .models import Artwork, Category
from accounts.serializers import ArtistProfileSerializer


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id","name","slug")


class ArtworkListSerializer(serializers.ModelSerializer):
    artist = ArtistProfileSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    class Meta:
        model = Artwork
        fields = ("id","slug","title","price","file_preview","artist","categories","tags","is_active","created_at")

class ArtworkCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artwork
        fields = ("title","description","price","file_original","file_preview","categories","tags")

class ArtworkDetailSerializer(serializers.ModelSerializer):
    artist = ArtistProfileSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    class Meta:
        model = Artwork
        fields = ("id","slug","title","description","price","file_preview","artist","categories","tags","is_active","created_at")

