from rest_framework import viewsets, permissions
from .models import Category, Artwork
from .serializers import CategorySerializer
from rest_framework import viewsets, permissions, mixins
from .serializers import ArtworkListSerializer, ArtworkDetailSerializer, ArtworkCreateSerializer
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import SAFE_METHODS, BasePermission, AllowAny, IsAuthenticated


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class IsArtistOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return (
            request.user.is_authenticated
            and getattr(request.user, "role", "") == "artist"
            and obj.artist.user_id == request.user.id
        )

class ArtworkViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    queryset = Artwork.objects.select_related("artist__user").prefetch_related("categories").order_by("-created_at")

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "categories__slug": ["exact"],  
        "price": ["gte", "lte"],      
        "artist__id": ["exact"],      
        "is_active": ["exact"],        
    }
    search_fields = ["title", "description", "tags", "artist__display_name"]
    ordering_fields = ["created_at", "price", "title"]  

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in ("list", "retrieve") and not self.request.user.is_staff:
            return qs.filter(is_active=True)
        return qs


    def get_serializer_class(self):
        if self.action == "list":
            return ArtworkListSerializer
        if self.action in ("create","update","partial_update"):
            return ArtworkCreateSerializer
        return ArtworkDetailSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action in ("create","update","partial_update","destroy"):
            return [IsAuthenticated(), IsArtistOwnerOrReadOnly()]
        return [AllowAny()]

    def perform_create(self, serializer):
        if getattr(self.request.user, "role", "") != "artist":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only artists can upload artworks.")
        serializer.save(artist=self.request.user.artist, is_active=False) 

    def get_permissions(self):
        if self.action in ("list","retrieve"):
            return [AllowAny()]
        return [IsAuthenticated(), IsArtistOwnerOrReadOnly()]
    
