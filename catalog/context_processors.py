from orders.cart import Cart  

def cart_context(request):
    try:
        count = len(Cart(request))
    except Exception:
        count = 0
    return {"cart_count": count}
