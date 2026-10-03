"""Test the signal receivers of the wopi app."""

from unittest import mock

import pytest

from core import factories, models
from core.signals import item_file_ready

pytestmark = pytest.mark.django_db


def _configure_clients(settings, options):
    settings.WOPI_CLIENTS = ["collabora"]
    settings.WOPI_CLIENTS_CONFIGURATION = {"collabora": {"options": options}}


def test_item_file_ready_queues_thumbnail_on_commit(settings, django_capture_on_commit_callbacks):
    """A ready file gets its thumbnail rendered once its state is committed."""
    _configure_clients(settings, {"ThumbnailServiceUrl": "http://collabora"})
    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE)

    with mock.patch("wopi.signals.generate_item_thumbnail") as task:
        with django_capture_on_commit_callbacks() as callbacks:
            item_file_ready.send(sender=models.Item, item=item)
        task.delay.assert_not_called()

        for callback in callbacks:
            callback()

    task.delay.assert_called_once_with(str(item.id))


def test_item_file_ready_without_thumbnails(settings, django_capture_on_commit_callbacks):
    """Nothing is queued when no client opted in to thumbnails."""
    _configure_clients(settings, {"ConvertServiceUrl": "http://collabora"})
    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE)

    with (
        mock.patch("wopi.signals.generate_item_thumbnail") as task,
        django_capture_on_commit_callbacks(execute=True),
    ):
        item_file_ready.send(sender=models.Item, item=item)

    task.delay.assert_not_called()
