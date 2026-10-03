"""Signal receivers of the wopi app."""

from functools import partial

from django.db import transaction
from django.dispatch import receiver

from core.signals import item_file_ready
from wopi.conversion.thumbnails import resolve_thumbnail_backend
from wopi.tasks.thumbnails import generate_item_thumbnail


@receiver(item_file_ready)
def queue_item_thumbnail(sender, item, **kwargs):  # pylint: disable=unused-argument
    """Render the thumbnail of a file once its ready state is committed."""
    if resolve_thumbnail_backend() is None:
        return
    transaction.on_commit(partial(generate_item_thumbnail.delay, str(item.id)))
