"""Management command to queue thumbnail generation for existing files."""

from django.core.management.base import BaseCommand, CommandError

from core import models
from wopi.conversion.thumbnails import resolve_thumbnail_backend
from wopi.tasks.thumbnails import generate_item_thumbnail


class Command(BaseCommand):
    """Queue thumbnail generation for every ready file."""

    def handle(self, *args, **options):
        """Handle the command."""
        if resolve_thumbnail_backend() is None:
            raise CommandError("No WOPI client defines a ThumbnailServiceUrl option.")

        items = models.Item.objects.filter(
            type=models.ItemTypeChoices.FILE,
            upload_state=models.ItemUploadStateChoices.READY,
            deleted_at__isnull=True,
        ).values_list("id", flat=True)

        for item_id in items.iterator():
            generate_item_thumbnail.delay(str(item_id))
