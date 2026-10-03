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
from wopi.utils import is_item_wopi_supported

BACKENDS = {
    "collabora": CollaboraConversionBackend,
    "onlyoffice": OnlyOfficeConversionBackend,
}


def resolve_thumbnail_backend():
    """Return a backend for the first WOPI client opting in with a ThumbnailServiceUrl."""
    for client in settings.WOPI_CLIENTS:
        options = settings.WOPI_CLIENTS_CONFIGURATION.get(client, {}).get("options", {})
        thumbnail_service_url = options.get("ThumbnailServiceUrl")
        if thumbnail_service_url and client in BACKENDS:
            return BACKENDS[client](convert_service_url=thumbnail_service_url)
    return None


def generate_thumbnail(item):
    """Render, resize and store the item thumbnail. Return False when not applicable."""
    backend = resolve_thumbnail_backend()
    if (
        backend is None
        or item.upload_state != models.ItemUploadStateChoices.READY
        # The item is ready so no user is needed to tell whether the client supports it.
        or not is_item_wopi_supported(item, None)
    ):
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
