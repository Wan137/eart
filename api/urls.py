from django.urls import path, include
from rest_framework.routers import DefaultRouter
from accounts.views import ArtistProfileViewSet
from catalog.views import CategoryViewSet, ArtworkViewSet
from orders.views import CartView, CartAddView, CartSetQtyView, CartRemoveView, CartClearView, CheckoutView
from downloads.views import download_original
from orders.views import OrderViewSet



from orders.views import (
    CartView, CartAddView, CartSetQtyView, CartRemoveView, CartClearView,
    CheckoutView, OrderViewSet,
)

router = DefaultRouter()
router.register(r"artists", ArtistProfileViewSet, basename="artists")
router.register(r"categories", CategoryViewSet, basename="categories")
router.register(r"artworks", ArtworkViewSet, basename="artworks")
router.register(r"orders", OrderViewSet, basename="orders")

urlpatterns = [
    path("", include(router.urls)),
    # cart
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/add/", CartAddView.as_view(), name="cart_add"),
    path("cart/set/<int:artwork_id>/", CartSetQtyView.as_view(), name="cart_set"),
    path("cart/remove/<int:artwork_id>/", CartRemoveView.as_view(), name="cart_remove"),
    path("cart/clear/", CartClearView.as_view(), name="cart_clear"),
    # checkout + downloads
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("downloads/<uuid:token>/", download_original, name="download"),
]
