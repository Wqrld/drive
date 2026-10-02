"""Celery tasks for WOPI document thumbnails."""

import logging

from core import models
from wopi.conversion.exceptions import ConversionProviderError
from wopi.conversion.thumbnails import generate_thumbnail

from drive.celery_app import app

logger = logging.getLogger(__name__)


@app.task(
    autoretry_for=(ConversionProviderError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def generate_item_thumbnail(item_id):
    """Render the thumbnail of a ready item."""
    try:
        item = models.Item.objects.get(id=item_id)
    except models.Item.DoesNotExist:
        logger.error("generate_item_thumbnail: item %s does not exist, aborting", item_id)
        return

    generate_thumbnail(item)
