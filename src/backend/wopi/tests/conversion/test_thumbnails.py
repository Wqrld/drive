"""Tests for document thumbnail generation."""

from datetime import UTC, datetime
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


def _render_time(hour):
    """Fix the time a thumbnail is rendered at, without freezing the S3 request signing."""
    return mock.patch(
        "wopi.conversion.thumbnails.timezone.now",
        return_value=datetime(2024, 10, 3, hour, tzinfo=UTC),
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


def test_resolve_thumbnail_backend_requires_opt_in(settings):
    """A ConvertServiceUrl alone, set for legacy conversion, does not enable thumbnails."""
    _configure_wopi(
        settings,
        {"onlyoffice": {"ConvertServiceUrl": "http://onlyoffice/converter"}},
    )

    assert thumbnails.resolve_thumbnail_backend() is None


def test_resolve_thumbnail_backend_ignores_unknown_client(settings):
    """A client without a known backend cannot render thumbnails."""
    _configure_wopi(settings, {"vendorA": {"ThumbnailServiceUrl": "https://vendorA.example"}})

    assert thumbnails.resolve_thumbnail_backend() is None


def test_resolve_thumbnail_backend_picks_first_client_opting_in(settings):
    """The first client defining a ThumbnailServiceUrl renders thumbnails."""
    _configure_wopi(
        settings,
        {
            "collabora": {},
            "onlyoffice": {"ThumbnailServiceUrl": "http://onlyoffice/converter"},
        },
    )

    backend = thumbnails.resolve_thumbnail_backend()

    assert isinstance(backend, OnlyOfficeConversionBackend)
    assert backend.convert_service_url == "http://onlyoffice/converter"


def test_generate_thumbnail_stores_resized_png(settings):
    """Store the rendered first page resized to WOPI_THUMBNAIL_SIZE and record when."""
    settings.WOPI_THUMBNAIL_SIZE = 64
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file()
    assert item.thumbnail_key is None

    with (
        mock.patch.object(
            CollaboraConversionBackend,
            "thumbnail",
            side_effect=lambda *_: ContentFile(_png(800, 1200)),
        ),
        _render_time(12),
    ):
        assert thumbnails.generate_thumbnail(item) is True

    item.refresh_from_db()
    assert item.thumbnail_key == f"item/{item.id!s}/thumbnail/1727956800000.png"
    with default_storage.open(item.thumbnail_key) as file:
        assert Image.open(file).size == (43, 64)


def test_generate_thumbnail_replaces_previous_thumbnail(settings):
    """A new render gets a new key, so browsers cannot serve the old one from cache."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file()

    with mock.patch.object(
        CollaboraConversionBackend,
        "thumbnail",
        side_effect=lambda *_: ContentFile(_png(80, 120)),
    ):
        with _render_time(12):
            thumbnails.generate_thumbnail(item)
        previous_key = item.thumbnail_key
        with _render_time(13):
            thumbnails.generate_thumbnail(item)
        # Rendering twice within the same millisecond keeps a single file.
        with _render_time(13):
            thumbnails.generate_thumbnail(item)

    item.refresh_from_db()
    assert item.thumbnail_key != previous_key
    assert default_storage.exists(item.thumbnail_key)
    assert not default_storage.exists(previous_key)
    _dirs, files = default_storage.listdir(f"item/{item.id!s}/thumbnail")
    assert files == [item.thumbnail_key.rsplit("/", 1)[1]]


def test_generate_thumbnail_does_not_depend_on_the_creator(settings):
    """Thumbnails are rendered for ready files whose creator is gone."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file()
    item.creator = None

    with mock.patch.object(
        CollaboraConversionBackend, "thumbnail", return_value=ContentFile(_png(80, 120))
    ):
        assert thumbnails.generate_thumbnail(item) is True


@pytest.mark.parametrize(
    "upload_state",
    [
        models.ItemUploadStateChoices.ANALYZING,
        models.ItemUploadStateChoices.SUSPICIOUS,
        models.ItemUploadStateChoices.FILE_TOO_LARGE_TO_ANALYZE,
    ],
)
def test_generate_thumbnail_skips_files_not_ready(settings, upload_state):
    """Only ready files get a thumbnail."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="report.docx",
        update_upload_state=upload_state,
    )

    with mock.patch.object(CollaboraConversionBackend, "thumbnail") as thumbnail:
        assert thumbnails.generate_thumbnail(item) is False

    thumbnail.assert_not_called()


def test_generate_thumbnail_skips_unsupported_item(settings):
    """Files the WOPI client does not support get no thumbnail."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file("photo.png")

    with mock.patch.object(CollaboraConversionBackend, "thumbnail") as thumbnail:
        assert thumbnails.generate_thumbnail(item) is False

    thumbnail.assert_not_called()
    item.refresh_from_db()
    assert item.thumbnail_updated_at is None
