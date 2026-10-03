"""Signal receivers of the wopi app."""

from functools import partial

from django.db import transaction
from django.dispatch import receiver

from core.signals import item_file_ready
from wopi.conversion.thumbnails import thumbnail_clients
from wopi.tasks.thumbnails import generate_item_thumbnail


@receiver(item_file_ready)
def queue_item_thumbnail(sender, item, **kwargs):  # pylint: disable=unused-argument
    """Render the thumbnail of a file once its ready state is committed."""
    if not any(thumbnail_clients()):
        return
    transaction.on_commit(partial(generate_item_thumbnail.delay, str(item.id)))
