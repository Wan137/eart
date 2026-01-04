# catalog/web_urls.py
from django.urls import path
from . import web_views

urlpatterns = [
    path("", web_views.catalog_view, name="web_catalog"),
    path("art/<slug:slug>/", web_views.artwork_detail, name="web_artwork_detail"),

    path("cart/", web_views.cart_view, name="web_cart"),
    path("cart/add/<int:artwork_id>/", web_views.web_cart_add, name="web_cart_add"),
    path("checkout/", web_views.checkout_view, name="web_checkout"),
    path("cart/remove/<int:artwork_id>/", web_views.cart_remove_view, name="web_cart_remove"),

    path("artist/<str:username>/", web_views.artist_view, name="web_artist"),
    path("studio/", web_views.studio_my_artworks, name="web_studio_list"),
    path("studio/new/", web_views.studio_artwork_create, name="web_studio_create"),
    path("studio/stats/", web_views.studio_stats_view, name="web_studio_stats"),

    path("my/orders/", web_views.my_orders_view, name="web_my_orders"),
    path("my/orders/<int:order_id>/resend/", web_views.my_order_resend_links, name="web_my_order_resend"),
    path("my/orders/<int:order_id>/", web_views.my_order_detail_view, name="web_my_order_detail"),
    path('profile/edit/', web_views.edit_profile_view, name='edit_profile'),

    path("pay/stripe/<int:order_id>/", web_views.pay_with_stripe_view, name="web_pay_stripe"),
    path("stripe/success/", web_views.checkout_success_view, name="web_stripe_success"),
    path("stripe/webhook/", web_views.stripe_webhook_view, name="web_stripe_webhook"),
    path('favorite/<slug:slug>/', web_views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', web_views.my_favorites, name='web_favorites'),
]


