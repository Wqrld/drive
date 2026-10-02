"""Tests for document thumbnail generation."""

from io import BytesIO
from unittest import mock

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

import pytest
from PIL import Image

from core import factories, models
from wopi.conversion import thumbnails
from wopi.conversion.backends.collabora import CollaboraConversionBackend
from wopi.conversion.backends.onlyoffice import OnlyOfficeConversionBackend
from wopi.tasks.configure_wopi import WOPI_CONFIGURATION_CACHE_KEY

pytestmark = pytest.mark.django_db


def _configure_wopi(settings, clients):
    """Configure WOPI clients with their options and a discovery covering .docx files."""
    settings.WOPI_CLIENTS = list(clients)
    settings.WOPI_CLIENTS_CONFIGURATION = {
        client: {"options": options} for client, options in clients.items()
    }
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {},
            "extensions": {
                "docx": {"url": "https://office.example/launch", "client": next(iter(clients))}
            },
        },
    )


def _png(width, height):
    """Return the bytes of a blank PNG image."""
    buffer = BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _file(filename="report.docx"):
    """Create a ready file."""
    return factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename=filename,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )


def test_resolve_thumbnail_backend_without_convert_service_url(settings):
    """Thumbnails are disabled when no client defines a ConvertServiceUrl."""
    _configure_wopi(settings, {"collabora": {"SupportsRename": False}})

    assert thumbnails.resolve_thumbnail_backend() is None


def test_resolve_thumbnail_backend_ignores_unknown_client(settings):
    """A client without a known backend cannot render thumbnails."""
    _configure_wopi(settings, {"vendorA": {"ConvertServiceUrl": "https://vendorA.example"}})

    assert thumbnails.resolve_thumbnail_backend() is None


def test_resolve_thumbnail_backend_picks_first_client_defining_url(settings):
    """The first client defining a ConvertServiceUrl renders thumbnails."""
    _configure_wopi(
        settings,
        {
            "collabora": {},
            "onlyoffice": {"ConvertServiceUrl": "http://onlyoffice/converter"},
        },
    )

    backend = thumbnails.resolve_thumbnail_backend()

    assert isinstance(backend, OnlyOfficeConversionBackend)
    assert backend.convert_service_url == "http://onlyoffice/converter"


def test_generate_thumbnail_stores_resized_png(settings):
    """Store the rendered first page resized to WOPI_THUMBNAIL_SIZE, replacing older ones."""
    settings.WOPI_THUMBNAIL_SIZE = 64
    _configure_wopi(settings, {"collabora": {"ConvertServiceUrl": "http://collabora"}})
    item = _file()

    with mock.patch.object(
        CollaboraConversionBackend,
        "thumbnail",
        side_effect=lambda *_: ContentFile(_png(800, 1200)),
    ):
        assert thumbnails.generate_thumbnail(item) is True
        assert thumbnails.generate_thumbnail(item) is True

    with default_storage.open(item.thumbnail_key) as file:
        assert Image.open(file).size == (43, 64)


def test_generate_thumbnail_skips_unsupported_item(settings):
    """Files the WOPI client does not support get no thumbnail."""
    _configure_wopi(settings, {"collabora": {"ConvertServiceUrl": "http://collabora"}})
    item = _file("photo.png")

    with mock.patch.object(CollaboraConversionBackend, "thumbnail") as thumbnail:
        assert thumbnails.generate_thumbnail(item) is False

    thumbnail.assert_not_called()
    assert not default_storage.exists(item.thumbnail_key)
