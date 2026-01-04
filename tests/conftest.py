import pytest
from django.conf import settings

@pytest.fixture(autouse=True)
def _tmp_media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    return settings
