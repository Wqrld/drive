"""Render document thumbnails through the configured WOPI provider."""

from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from PIL import Image

from core import models
from wopi.conversion.backends.collabora import CollaboraConversionBackend
from wopi.conversion.backends.onlyoffice import OnlyOfficeConversionBackend
from wopi.utils import get_wopi_configuration

BACKENDS = {
    "collabora": CollaboraConversionBackend,
    "onlyoffice": OnlyOfficeConversionBackend,
}

# The frontend shows these images through their own preview, they need no thumbnail.
BROWSER_IMAGE_MIMETYPES = {
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/svg+xml",
    "image/webp",
}


def thumbnail_clients():
    """Yield (client, ThumbnailServiceUrl) of the WOPI clients opting in, in order."""
    for client in settings.WOPI_CLIENTS:
        options = settings.WOPI_CLIENTS_CONFIGURATION.get(client, {}).get("options", {})
        thumbnail_service_url = options.get("ThumbnailServiceUrl")
        if thumbnail_service_url and client in BACKENDS:
            yield client, thumbnail_service_url


def resolve_thumbnail_backend(item):
    """Return a backend for the first client opting in that can render the item."""
    configuration = get_wopi_configuration()
    extension = item.extension.lower() if item.extension else None
    for client, thumbnail_service_url in thumbnail_clients():
        renderable = configuration.get(client, {}).get("renderable", {})
        if extension in renderable.get("extensions", ()) or item.mimetype in renderable.get(
            "mimetypes", ()
        ):
            return BACKENDS[client](convert_service_url=thumbnail_service_url)
    return None


def generate_thumbnail(item):
    """Render, resize and store the item thumbnail. Return False when not applicable."""
    if (
        item.upload_state != models.ItemUploadStateChoices.READY
        or item.mimetype in BROWSER_IMAGE_MIMETYPES
    ):
        return False
    backend = resolve_thumbnail_backend(item)
    if backend is None:
        return False

    size = settings.WOPI_THUMBNAIL_SIZE
    image = Image.open(backend.thumbnail(item, size))
    image.thumbnail((size, size))
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    previous_key = item.thumbnail_key
    item.thumbnail_updated_at = timezone.now()
    # save() never overwrites, it would suffix the key instead.
    default_storage.delete(item.thumbnail_key)
    default_storage.save(item.thumbnail_key, ContentFile(buffer.getvalue()))
    # update() skips the post_save signal, a new thumbnail is no reason to reindex the item.
    models.Item.objects.filter(pk=item.pk).update(thumbnail_updated_at=item.thumbnail_updated_at)

    if previous_key and previous_key != item.thumbnail_key:
        default_storage.delete(previous_key)
    return True
