from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponseForbidden
from .models import DownloadToken, DownloadLog

def download_original(request, token):
    link = get_object_or_404(DownloadToken, token=token)
    if not link.is_valid():
        return HttpResponseForbidden("Link expired or exhausted")

    DownloadLog.objects.create(
        token=link,
        ip=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT",""),
    )

    link.remaining -= 1
    link.save(update_fields=["remaining"])

    f = link.order_item.artwork.file_original
    return FileResponse(f.open("rb"), as_attachment=True, filename=f.name.split("/")[-1])
