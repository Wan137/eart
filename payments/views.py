import stripe, json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest
from django.conf import settings
from orders.models import Order, OrderItem
from downloads.models import DownloadToken
from django.utils import timezone

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponseBadRequest("invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")
        if not order_id:
            return HttpResponse("no order id", status=200)

        try:
            order = Order.objects.select_related("user").prefetch_related("items__artwork").get(id=order_id)
        except Order.DoesNotExist:
            return HttpResponse("order not found", status=200)

        if order.status != "paid":
            order.status = "paid"
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at"])

            for it in order.items.all():
                DownloadToken.objects.create(
                    order_item=it,
                    remaining=3,    
                    expires_at=timezone.now() + timezone.timedelta(days=7),
                )

    return HttpResponse(status=200)
