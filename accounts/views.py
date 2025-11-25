from django.shortcuts import render, redirect
from rest_framework import viewsets, permissions
from .models import ArtistProfile
from .serializers import ArtistProfileSerializer
from .forms import SignUpForm
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import get_user_model

class IsArtistOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return True
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(request.user, "role", "") == "artist" and obj.user_id == request.user.id

class ArtistProfileViewSet(viewsets.ModelViewSet):
    queryset = ArtistProfile.objects.select_related("user")
    serializer_class = ArtistProfileSerializer
    permission_classes = [IsArtistOrReadOnly]

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)
    
User = get_user_model()

def signup_view(request):
    if request.user.is_authenticated:
        return redirect("/")  # уже вошёл

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)  # сразу залогинить
            messages.success(request, "Welcome! Your account has been created.")
            # куда везти после регистрации:
            if getattr(user, "role", "") == "artist":
                return redirect("/studio/")
            return redirect("/")
    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})
