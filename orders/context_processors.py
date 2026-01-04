from .cart import Cart

def cart_meta(request):
    try:
        count = Cart(request).count()
    except Exception:
        count = 0
    return {"cart_count": count}
