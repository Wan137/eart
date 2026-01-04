import email
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
from .forms import UserUpdateForm, ArtistProfileForm
from catalog.models import Favorite
from .forms import ReviewForm
from .models import Review

TOKEN_LIFETIME_DAYS = 7
TOKEN_DEFAULT_REMAINING = 3
RESEND_COOLDOWN_MIN = 10


def cart_view(request):
    cart = Cart(request)
    return render(request, "pages/cart.html", {"cart": cart})

def checkout_view(request):
    cart = Cart(request)
    if not cart.data:
        messages.info(request, "Your cart is empty.")
        return redirect("web_cart")

    if request.method == "GET":
        return render(request, "pages/checkout.html", {"cart": cart})

    email = request.POST.get("email")
    full_name = request.POST.get("full_name")
    address = request.POST.get("address")

    if not email or not full_name:
        messages.error(request, "Please fill in email and full name.")
        return render(request, "pages/checkout.html", {"cart": cart})

    order = Order.objects.create(
        email=email,
        full_name=full_name,
        total_amount=cart.get_total_price(),
        status="pending"  
    )
    
    if request.user.is_authenticated:
        order.user = request.user
        order.save()

    for item in cart:
        product = item['art']
        OrderItem.objects.create(
            order=order,
            artwork=product,
            unit_price=product.price,
            qty=item['qty']
        )

    cart.clear()
    
    return redirect("web_pay_stripe", order_id=order.id)

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

def artwork_detail(request, slug):
    artwork = get_object_or_404(Artwork, slug=slug)
    
    if request.method == 'POST' and request.user.is_authenticated:
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.artwork = artwork
            review.save()
            return redirect('web_artwork_detail', slug=slug)
    else:
        form = ReviewForm()

    reviews = artwork.reviews.all().order_by('-created_at')
    
    return render(request, 'pages/artwork_detail.html', {
        'artwork': artwork, 
        'item': artwork,     
        'object': artwork,   
        'product': artwork, 
        'reviews': reviews,
        'form': form
    })


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
    try:
        artist = ArtistProfile.objects.get(user=request.user)
    except ArtistProfile.DoesNotExist:
        print("!!! ОШИБКА: У этого юзера нет ArtistProfile !!!")
        messages.error(request, "You need an Artist Profile to upload art.")
        return redirect("web_studio_list") 

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

            print(f"!!! УСПЕХ: Картина '{art.title}' сохранена! ID: {art.id}")
            messages.success(request, "Artwork submitted.")
            return redirect("web_studio_list")
        else:
            print("!!! ОШИБКА ФОРМЫ (FORM INVALID) !!!")
            print(form.errors)
            messages.error(request, "Error saving artwork. Check the form.")
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

    total_sold = sold_qs.count()
    revenue = sold_qs.aggregate(sum=Sum("unit_price"))["sum"] or 0

    ctx = {
        "total": total_artworks,      
        "published": active_artworks, 
        "pending": pending_artworks,   
        "sold": total_sold,            
        "revenue": revenue,           
        "total_artworks": total_artworks,
        "total_items": total_sold,
    }
    return render(request, "pages/studio_stats.html", ctx)

@login_required
def my_orders_view(request):
    qs = Order.objects.all().order_by("-created_at")

    user_email = (getattr(request.user, "email", "") or "").strip()

    filter_condition = Q()

    if hasattr(Order, "user"):
        filter_condition |= Q(user=request.user)

    if user_email:
        filter_condition |= Q(email__iexact=user_email)

    if filter_condition:
        qs = qs.filter(filter_condition)
    else:
        qs = qs.none()

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
    order = get_object_or_404(Order, id=order_id)

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
    order = get_object_or_404(Order, id=order_id)
    
    email = getattr(order, 'email', '')
    if not email and request.user.is_authenticated:
        email = request.user.email
        
    full_name = getattr(order, 'full_name', 'Guest')

    if request.method == "POST":
        if not email:
            messages.error(request, "No email found for this order.")
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
        
        try:
            body = render(request, "emails/order_links.txt", ctx).content.decode()
        except Exception:
            body = f"Here are your links: \n" + "\n".join([i['url'] for i in items])

        try:
            send_mail(
                subject=f"Order #{order.id} Downloads",
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, f"Email sent to {email}!")
        except Exception as e:
            print(f"EMAIL ERROR: {e}") 
            messages.warning(request, "Email simulation: check your server console.")

        return redirect("web_my_order_detail", order_id=order.id)

    return redirect("web_my_order_detail", order_id=order.id)



@login_required
def pay_with_stripe_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    domain_url = request.scheme + '://' + request.get_host()
    
    line_items = []
    for item in order.items.all():
        image_url = ""
        if item.artwork.file_preview:
            image_url = domain_url + item.artwork.file_preview.url

        line_items.append({
            'price_data': {
                'currency': 'myr',
                'unit_amount': int(item.unit_price * 100),
                'product_data': {
                    'name': item.artwork.title,
                    'images': [image_url] if image_url else [],
                },
            },
            'quantity': item.qty,
        })

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=domain_url + f'/stripe/success/?order_id={order.id}',
        cancel_url=domain_url + f'/my/orders/{order.id}/',
    )
    
    return redirect(session.url, code=303)

@require_GET
def checkout_success_view(request):
    order_id = request.GET.get('order_id')
    
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            
            if order.status != 'paid':
                order.status = 'paid'
                order.save()
                
                for it in order.items.all():
                    DownloadToken.objects.get_or_create(
                        order_item=it,
                        defaults={
                            'expires_at': timezone.now() + timedelta(days=7),
                            'remaining': 3
                        }
                    )
            
        except Order.DoesNotExist:
            pass

    return render(request, 'pages/success.html')

@csrf_exempt
def stripe_webhook_view(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception:
        return HttpResponseBadRequest("Invalid signature")

    if event["type"] == "checkout.session.completed":
        data = event["data"]["object"]
        order_id = data.get("metadata", {}).get("order_id")

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return HttpResponse(status=200)

        if order.status != "paid":
            order.status = "paid"
            order.save(update_fields=["status"])

            for it in order.items.select_related("artwork"):
                DownloadToken.objects.create(
                    order_item=it,
                    expires_at=timezone.now() + timezone.timedelta(days=7),
                    remaining=3,
                )

    return HttpResponse(status=200)

@require_POST
def web_cart_add(request, artwork_id):
    art_id = artwork_id
    qty = int(request.POST.get("qty", 1))
    if not art_id:
        return HttpResponseBadRequest("artwork_id required")

    Cart(request).add(art_id, qty)
    messages.success(request, "Artwork added to cart!")
    return redirect(request.META.get("HTTP_REFERER", "web_cart"))


@login_required
def edit_profile_view(request):
    user = request.user
    
    if hasattr(user, 'artistprofile'):
        artist_profile = user.artistprofile
    else:
        artist_profile = None

    if request.method == 'POST':
        if 'become_artist' in request.POST:
            obj, created = ArtistProfile.objects.get_or_create(user=user)
            
            user.role = 'artist'
            user.save()

            if not obj.display_name:
                obj.display_name = user.username
                obj.save()
            
            messages.success(request, "Congratulations! You are now an Artist.")
            return redirect('edit_profile')

        user_form = UserUpdateForm(request.POST, instance=user)
        
        profile_form = None
        if artist_profile:
            profile_form = ArtistProfileForm(request.POST, request.FILES, instance=artist_profile)

        if user_form.is_valid():
            user_form.save()
            if profile_form and profile_form.is_valid():
                profile_form.save()
            
            messages.success(request, "Profile updated successfully!")
            return redirect('edit_profile')

    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = None
        if artist_profile:
            profile_form = ArtistProfileForm(instance=artist_profile)

    return render(request, 'pages/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'is_artist': (artist_profile is not None)
    })

@login_required
def toggle_favorite(request, slug):
    artwork = get_object_or_404(Artwork, slug=slug)
    fav, created = Favorite.objects.get_or_create(user=request.user, artwork=artwork)
    
    if not created:
        fav.delete()
        is_liked = False
    else:
        is_liked = True

    return render(request, 'partials/like_button.html', {
        'artwork': artwork,
        'is_liked': is_liked
    })

@login_required
def my_favorites(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('artwork').order_by('-created_at')
    return render(request, 'pages/favorites.html', {'favorites': favorites})