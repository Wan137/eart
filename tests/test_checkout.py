import io
import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User, ArtistProfile
from catalog.models import Artwork
from downloads.models import DownloadToken

@pytest.mark.django_db
def test_checkout_creates_order_and_download_token(client):
    # 1) создаём художника
    artist_user = User.objects.create_user(username="artist", password="x", role="artist")
    artist = ArtistProfile.objects.create(user=artist_user, display_name="Artist A")

    # 2) создаём файл-оригинал (псевдо-картинка)
    content = SimpleUploadedFile("orig.jpg", b"\x00\x01\x02", content_type="image/jpeg")

    # 3) арт-объект, активен
    art = Artwork.objects.create(
        artist=artist,
        title="Test Art",
        price=10,
        is_active=True,
        file_original=content,
    )

    # 4) кладём в корзину через сессию
    session = client.session
    session["cart"] = {str(art.id): 1}
    session.save()

    # 5) делаем checkout
    url = reverse("checkout")
    resp = client.post(
        url,
        data={"email": "buyer@example.com", "full_name": "Buyer"},
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()
    assert data["paid"] is True
    assert data["items"], "Order must have items"

    # 6) проверяем, что создан токен
    assert DownloadToken.objects.count() == 1
    token = DownloadToken.objects.first()
    assert token.remaining == 3
