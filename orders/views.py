from rest_framework import views, status, permissions, viewsets
from rest_framework.response import Response
from django.db import transaction
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from catalog.models import Artwork
from .models import Order, OrderItem
from downloads.models import DownloadToken
from .serializers import OrderSerializer
from .cart import Cart


class CartView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cart = Cart(request)
        data = list(cart.items())
        return Response({
            "items": data,
            "total": str(cart.total()),
        })


class CartAddView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        artwork_id = request.data.get("artwork_id")
        qty = int(request.data.get("qty", 1))
        if not artwork_id:
            return Response({"detail": "artwork_id required"}, status=400)
        if not Artwork.objects.filter(id=artwork_id, is_active=True).exists():
            return Response({"detail": "Artwork not found or inactive"}, status=404)
        Cart(request).add(artwork_id, qty)
        return Response({"detail": "added"}, status=201)


class CartSetQtyView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, artwork_id):
        qty = int(request.data.get("qty", 1))
        Cart(request).set(artwork_id, qty)
        return Response({"detail": "updated"})


class CartRemoveView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def delete(self, request, artwork_id):
        Cart(request).remove(artwork_id)
        return Response(status=204)


class CartClearView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        Cart(request).clear()
        return Response({"detail": "cleared"})


class CheckoutView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        cart = Cart(request)
        if not cart.data:
            return Response({"detail": "Cart is empty"}, status=400)

        email = request.data.get("email")
        full_name = request.data.get("full_name")
        if not email or not full_name:
            return Response({"detail": "email and full_name are required"}, status=400)

        ids = [int(k) for k in cart.data.keys()]
        artworks = list(Artwork.objects.filter(id__in=ids, is_active=True))
        if not artworks:
            return Response({"detail": "No valid artworks"}, status=400)

        price_map = {a.id: a.price for a in artworks}

        with transaction.atomic():
            total = sum(Decimal(price_map[int(k)]) * int(v) for k, v in cart.data.items())
            order = Order.objects.create(
                buyer=request.user if request.user.is_authenticated else None,
                email=email,
                full_name=full_name,
                total_amount=total,
                status="paid",  
                paid=True,    
            )

            for art in artworks:
                qty = int(cart.data[str(art.id)])
                item = OrderItem.objects.create(
                    order=order,
                    artwork=art,
                    unit_price=art.price,
                    qty=qty,
                )
                DownloadToken.objects.create(
                    order_item=item,
                    expires_at=timezone.now() + timedelta(days=3),
                    remaining=3,
                )

        cart.clear()
        return Response(OrderSerializer(order).data, status=201)


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.buyer_id == getattr(request.user, "id", None)

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        qs = Order.objects.prefetch_related("items__artwork__categories")
        if self.request.user.is_staff:
            return qs
        return qs.filter(buyer=self.request.user).order_by("-created_at")
