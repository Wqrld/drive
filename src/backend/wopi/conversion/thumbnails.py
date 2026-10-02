"""Render document thumbnails through the configured WOPI provider."""

from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from PIL import Image

from wopi.conversion.backends.collabora import CollaboraConversionBackend
from wopi.conversion.backends.onlyoffice import OnlyOfficeConversionBackend
from wopi.utils import is_item_wopi_supported

BACKENDS = {
    "collabora": CollaboraConversionBackend,
    "onlyoffice": OnlyOfficeConversionBackend,
}


def resolve_thumbnail_backend():
    """Return a backend for the first WOPI client defining a ConvertServiceUrl."""
    for client in settings.WOPI_CLIENTS:
        options = settings.WOPI_CLIENTS_CONFIGURATION[client].get("options", {})
        convert_service_url = options.get("ConvertServiceUrl")
        if convert_service_url and client in BACKENDS:
            return BACKENDS[client](convert_service_url=convert_service_url)
    return None


def generate_thumbnail(item):
    """Render, resize and store the item thumbnail. Return False when not applicable."""
    backend = resolve_thumbnail_backend()
    if backend is None or not is_item_wopi_supported(item, item.creator):
        return False

    size = settings.WOPI_THUMBNAIL_SIZE
    image = Image.open(backend.thumbnail(item, size))
    image.thumbnail((size, size))
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    # save() never overwrites, it would suffix the key instead.
    default_storage.delete(item.thumbnail_key)
    default_storage.save(item.thumbnail_key, ContentFile(buffer.getvalue()))
    return True
