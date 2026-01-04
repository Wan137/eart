from rest_framework import serializers
from .models import User, ArtistProfile

class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id","username","role")

class ArtistProfileSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    class Meta:
        model = ArtistProfile
        fields = ("id","user","display_name","bio")
