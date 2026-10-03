"""
Declare and configure the signals for the impress core application
"""

from functools import partial

from django.db import transaction
from django.db.models import signals
from django.dispatch import Signal, receiver

from . import models
from .tasks.search import trigger_batch_file_indexer

# Sent with an `item` argument when the content of a file item is ready to be served,
# after its malware analysis or a conversion. Sent again each time the content changes.
item_file_ready = Signal()


@receiver(signals.post_save, sender=models.Item)
def file_post_save(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """
    Asynchronous call to the document indexer at the end of the transaction.
    Note : Within the transaction we can have an empty content and a serialization
    error.
    """
    transaction.on_commit(partial(trigger_batch_file_indexer, instance))


@receiver(signals.post_save, sender=models.ItemAccess)
def file_access_post_save(sender, instance, created, **kwargs):  # pylint: disable=unused-argument
    """
    Asynchronous call to the document indexer at the end of the transaction.
    """
    if not created:
        transaction.on_commit(partial(trigger_batch_file_indexer, instance.item))
