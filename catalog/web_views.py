from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Artwork, Category
from orders.cart import Cart
import requests
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.http import HttpResponseBadRequest
from django.contrib import messages
from django.core.paginator import Paginator
from accounts.models import ArtistProfile
from .forms import ArtworkForm
from accounts.decorators import artist_required
from django.utils.text import slugify
from orders.models import Order, OrderItem
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from downloads.models import DownloadToken
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum, Count, F
from datetime import timedelta
from orders.models import OrderItem
import stripe
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
import json 

TOKEN_LIFETIME_DAYS = 7
TOKEN_DEFAULT_REMAINING = 3
RESEND_COOLDOWN_MIN = 10


def cart_view(request):
    cart = Cart(request)
    return render(request, "pages/cart.html", {"cart": cart})

def checkout_view(request):
    """
    GET  -> страница чекаута
    POST -> вызов API /api/checkout/, показ успеха/ошибки
    """
    cart = Cart(request)

    # Пустая корзина — отправляем обратно
    if not cart.data:
        messages.info(request, "Your cart is empty.")
        return redirect("web_cart")

    if request.method == "GET":
        return render(request, "pages/checkout.html", {"cart": cart})

    # POST
    email = request.POST.get("email")
    full_name = request.POST.get("full_name")
    address = request.POST.get("address") 

    if not email or not full_name:
        messages.error(request, "Please fill in email and full name.")
        return render(request, "pages/checkout.html", {"cart": cart})

    try:
        resp = requests.post(
            "http://127.0.0.1:8000/api/checkout/",
            json={"email": email, "full_name": full_name, "address": address},
            cookies=request.COOKIES,
            timeout=10,
        )
    except requests.RequestException:
        messages.error(request, "Checkout service is unavailable. Try again later.")
        return render(request, "pages/checkout.html", {"cart": cart})

    if resp.status_code == 201:
        data = resp.json()
        order_id = data["id"] 
        # return redirect("web_pay_stripe", order_id=order_id)

    try:
        err = resp.json().get("detail", resp.text)
    except Exception:
        err = resp.text
    messages.error(request, f"Checkout failed: {err}")
    return render(request, "pages/checkout.html", {"cart": cart})

def catalog_view(request):
    q = request.GET.get("q","").strip()
    cat = request.GET.get("cat","").strip()
    ordering = request.GET.get("ordering","-created_at")

    qs = Artwork.objects.filter(is_active=True)\
        .select_related("artist__user")\
        .prefetch_related("categories")

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(tags__icontains=q) |
            Q(artist__display_name__icontains=q)
        )
    if cat:
        qs = qs.filter(categories__slug=cat)
    if ordering in {"-created_at","created_at","price","-price","title","-title"}:
        qs = qs.order_by(ordering)

    categories = Category.objects.order_by("name")

    page_number = request.GET.get("page", 1)
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(page_number)

    return render(request, "pages/catalog.html", {
        "items": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "categories": categories,
        "q": q, "cat": cat, "ordering": ordering,
    })


def artist_view(request, username):
    artist = get_object_or_404(
        ArtistProfile.objects.select_related("user"),
        user__username=username
    )
    qs = Artwork.objects.filter(is_active=True, artist=artist).select_related("artist__user").prefetch_related("categories")
    page = request.GET.get("page", 1)
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(page)

    return render(request, "pages/artist.html", {
        "artist": artist,
        "items": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
    })

def artwork_detail_view(request, slug):
    art = get_object_or_404(
        Artwork.objects.select_related("artist__user").prefetch_related("categories"),
        slug=slug, is_active=True
    )
    related = Artwork.objects.filter(is_active=True, artist=art.artist).exclude(id=art.id)[:8]
    return render(request, "pages/artwork_detail.html", {"art": art, "related": related})

def cart_remove_view(request, artwork_id):
    cart = Cart(request)
    cart.remove(artwork_id)
    messages.success(request, "Removed from cart.")
    return redirect("web_cart")


@require_POST
def add_to_cart_view(request):
    art_id = request.POST.get("artwork_id")
    if not art_id:
        return HttpResponseBadRequest("artwork_id required")
    Cart(request).add(art_id)
    messages.success(request, "Artwork added to cart!")
    return redirect(request.META.get("HTTP_REFERER", "web_cart"))

def cart_remove_view(request, artwork_id):
    Cart(request).remove(artwork_id)
    messages.success(request, "Removed from cart.")
    return redirect("web_cart")


@artist_required
def studio_my_artworks(request):
    artist = ArtistProfile.objects.get(user=request.user)
    qs = Artwork.objects.filter(artist=artist).order_by("-created_at")
    return render(request, "pages/studio_list.html", {"items": qs})

@artist_required
def studio_artwork_create(request):
    artist = get_object_or_404(ArtistProfile, user=request.user)

    if request.method == "POST":
        form = ArtworkForm(request.POST, request.FILES)
        if form.is_valid():
            art = form.save(commit=False)
            art.artist = artist


            if not art.slug and art.title:
                base = slugify(art.title) or "artwork"
                s, i = base, 2
                while Artwork.objects.filter(slug=s).exists():
                    s = f"{base}-{i}"; i += 1
                art.slug = s

            art.is_active = False  
            art.save()
            form.save_m2m()

            messages.success(request, "Artwork submitted. It will appear after approval.")
            return redirect("web_studio_list")
    else:
        form = ArtworkForm()


    return render(request, "pages/studio_create.html", {"form": form})



@artist_required
def studio_stats_view(request):
    artist = get_object_or_404(ArtistProfile, user=request.user)
    total_artworks = Artwork.objects.filter(artist=artist).count()
    active_artworks = Artwork.objects.filter(artist=artist, is_active=True).count()
    pending_artworks = Artwork.objects.filter(artist=artist, is_active=False).count()

    sold_qs = (OrderItem.objects
               .select_related("order", "artwork")
               .filter(artwork__artist=artist, order__status="paid"))

    total_items = sold_qs.count()
    revenue = sold_qs.aggregate(sum=Sum(F("unit_price")))["sum"] or 0

    top_by_revenue = (sold_qs.values("artwork__id", "artwork__title")
                      .annotate(rev=Sum(F("unit_price")), cnt=Count("id"))
                      .order_by("-rev")[:10])

    tokens_qs = DownloadToken.objects.filter(order_item__artwork__artist=artist)
    tokens_total = tokens_qs.count()
    tokens_remaining = tokens_qs.aggregate(r=Sum("remaining"))["r"] or 0

    ctx = dict(
        total_artworks=total_artworks,
        active_artworks=active_artworks,
        pending_artworks=pending_artworks,
        total_items=total_items,
        revenue=revenue,
        top_by_revenue=top_by_revenue,
        tokens_total=tokens_total,
        tokens_remaining=tokens_remaining,
    )
    return render(request, "pages/studio_stats.html", ctx)

@login_required
def my_orders_view(request):
    qs = Order.objects.all().order_by("-created_at")

    if hasattr(Order, "user"):
        qs = qs.filter(user=request.user)
    else:
        email = (getattr(request.user, "email", "") or "").strip()
        qs = qs.filter(email__iexact=email)

    page_number = request.GET.get("page", 1)
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(page_number)

    orders_data = []
    now = timezone.now()
    for order in page_obj.object_list:
        items_qs = (OrderItem.objects
                    .select_related("artwork", "order")
                    .filter(order=order))
        items_data = []
        for it in items_qs:
            token = (DownloadToken.objects
                     .filter(order_item=it, expires_at__gt=now, remaining__gt=0)
                     .order_by("id")
                     .order_by("-expires_at")
                     .first())
            download_url = None
            if token:
                download_url = f"/api/downloads/{token.token}/"
            items_data.append({
                "title": it.artwork.title,
                "qty": getattr(it, "qty", 1),
                "unit_price": it.unit_price,
                "download_url": download_url,
            })
        orders_data.append({
            "id": order.id,
            "created_at": order.created_at,
            "status": getattr(order, "status", "paid"),
            "total": getattr(order, "total_amount", 0),
            "items": items_data,
        })

    return render(request, "pages/my_orders.html", {
        "orders": orders_data,
        "page_obj": page_obj,
        "paginator": paginator,
    })


@login_required
def my_order_detail_view(request, order_id: int):
    if hasattr(Order, "user"):
        order = get_object_or_404(Order.objects.all(), id=order_id, user=request.user)
    else:
        email = (getattr(request.user, "email", "") or "").strip()
        order = get_object_or_404(Order.objects.all(), id=order_id, email__iexact=email)

    items = (OrderItem.objects
             .select_related("artwork", "order")
             .filter(order=order))

    now = timezone.now()
    items_data = []
    for it in items:
        token = (DownloadToken.objects
                 .filter(order_item=it, expires_at__gt=now, remaining__gt=0)
                 .order_by("-id")         
                 .first())
        items_data.append({
            "title": it.artwork.title,
            "unit_price": it.unit_price,
            "qty": getattr(it, "qty", 1),
            "download_url": f"/api/downloads/{token.token}/" if token else None,
            "remaining": getattr(token, "remaining", 0) if token else 0,
            "expires_at": getattr(token, "expires_at", None) if token else None,
        })

    ctx = {
        "order": order,
        "items": items_data,
        "status": getattr(order, "status", "paid"),
        "total": getattr(order, "total_amount", 0),
        "created_at": getattr(order, "created_at", None),
    }
    return render(request, "pages/my_order_detail.html", ctx)


def _get_or_create_valid_token(order_item):
    now = timezone.now()
    token = (DownloadToken.objects
             .filter(order_item=order_item, expires_at__gt=now, remaining__gt=0)
             .order_by("-id")
             .first())
    if token:
        return token
    return DownloadToken.objects.create(
        order_item=order_item,
        expires_at=now + timedelta(days=TOKEN_LIFETIME_DAYS),
        remaining=TOKEN_DEFAULT_REMAINING,
    )

@login_required
def my_order_resend_links(request, order_id: int):
    if hasattr(Order, "user"):
        order = get_object_or_404(Order.objects.all(), id=order_id, user=request.user)
        email = order.email or getattr(request.user, "email", "")
        full_name = getattr(request.user, "get_full_name", lambda: "")() or request.user.username
    else:
        email = (getattr(request.user, "email", "") or "").strip()
        order = get_object_or_404(Order.objects.all(), id=order_id, email__iexact=email)
        full_name = getattr(request.user, "get_full_name", lambda: "")() or email

    if request.method != "POST":
        messages.error(request, "Invalid method.")
        return redirect("web_my_order_detail", order_id=order.id)

    key = f"resend_links_{order.id}_{request.user.id}"
    if cache.get(key):
        messages.warning(request, "You can resend links a bit later.")
        return redirect("web_my_order_detail", order_id=order.id)

    items = []
    for it in OrderItem.objects.select_related("artwork").filter(order=order):
        tok = _get_or_create_valid_token(it)
        url = request.build_absolute_uri(f"/api/downloads/{tok.token}/")
        items.append({
            "title": it.artwork.title,
            "url": url,
            "remaining": tok.remaining,
            "expires_at": tok.expires_at,
        })

    ctx = {"order": order, "items": items, "full_name": full_name}
    body = render(request, "emails/order_links.txt", ctx).content.decode()

    try:
        send_mail(
            subject=f"Your ArtMarket downloads — Order #{order.id}",
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@artmarket.local"),
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        messages.error(request, f"Failed to send email: {e}")
        return redirect("web_my_order_detail", order_id=order.id)

    cache.set(key, True, RESEND_COOLDOWN_MIN * 60)
    messages.success(request, "Download links were sent to your email.")
    return redirect("web_my_order_detail", order_id=order.id)


@artist_required
def studio_stats_view(request):
    artist = get_object_or_404(ArtistProfile, user=request.user)

    total = Artwork.objects.filter(artist=artist).count()
    published = Artwork.objects.filter(artist=artist, is_active=True).count()
    pending = Artwork.objects.filter(artist=artist, is_active=False).count()

    sold = OrderItem.objects.filter(artwork__artist=artist).count()
    revenue = (
        OrderItem.objects.filter(artwork__artist=artist)
        .aggregate(s=Sum("unit_price"))["s"] or 0
    )

    return render(request, "pages/studio_stats.html", {
        "total": total,
        "published": published,
        "pending": pending,
        "sold": sold,
        "revenue": revenue,
    })

# def pay_with_stripe_view(request, order_id):
#     order = get_object_or_404(Order, id=order_id, status="pending")

#     # защита от оплаты чужих заказов
#     if order.buyer_id:
#         if not request.user.is_authenticated or order.buyer_id != request.user.id:
#             return HttpResponseForbidden("This order is not yours.")
#     else:
#         if request.session.get("last_order_id") != order.id:
#             return HttpResponseForbidden("This guest order is not authorized for this session.")

#     stripe.api_key = settings.STRIPE_SECRET_KEY
#     amount_cents = int(order.total_amount * 100)

#     session = stripe.checkout.Session.create(
#         mode="payment",
#         success_url=request.build_absolute_uri(f"/my/orders/{order.id}/?paid=1"),
#         cancel_url=request.build_absolute_uri(f"/my/orders/{order.id}/"),
#         line_items=[{
#             "price_data": {
#                 "currency": "usd",
#                 "product_data": {"name": f"Order #{order.id}"},
#                 "unit_amount": amount_cents,
#             },
#             "quantity": 1,
#         }],
#         metadata={"order_id": str(order.id)},
#     )
#     return redirect(session.url)

# @require_GET
# def checkout_success_view(request):
#     session_id = request.GET.get("session_id")
#     if not session_id:
#         return redirect("/")

#     stripe.api_key = settings.STRIPE_SECRET_KEY
#     session = stripe.checkout.Session.retrieve(session_id)
#     order_id = session.get("metadata", {}).get("order_id")

#     order = get_object_or_404(Order, id=order_id)

#     if session.payment_status == "paid" and order.status != "paid":
#         order.status = "paid"
#         order.save(update_fields=["status"])

#     return render(request, "pages/checkout_success.html", {"order": order})

# @csrf_exempt
# def stripe_webhook_view(request):
#     payload = request.body
#     sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
#     endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
#     except Exception:
#         return HttpResponseBadRequest("Invalid signature")

#     if event["type"] == "checkout.session.completed":
#         data = event["data"]["object"]
#         order_id = data.get("metadata", {}).get("order_id")

#         try:
#             order = Order.objects.get(id=order_id)
#         except Order.DoesNotExist:
#             return HttpResponse(status=200)

#         if order.status != "paid":
#             order.status = "paid"
#             order.save(update_fields=["status"])

#             # сгенерировать download-токены для позиций
#             for it in order.items.select_related("artwork"):
#                 DownloadToken.objects.create(
#                     order_item=it,
#                     expires_at=timezone.now() + timezone.timedelta(days=7),
#                     remaining=3,
#                 )

#     return HttpResponse(status=200)

@require_POST
def web_cart_add(request):
    art_id = request.POST.get("artwork_id")
    qty = int(request.POST.get("qty", 1))
    if not art_id:
        return HttpResponseBadRequest("artwork_id required")

    Cart(request).add(art_id, qty)
    messages.success(request, "Artwork added to cart!")
    return redirect(request.META.get("HTTP_REFERER", "web_cart"))