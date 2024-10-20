import datetime
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from cove_ocds import models


class Command(BaseCommand):
    help = "Delete files created DELETE_FILES_AFTER_DAYS ago"

    def handle(self, *args, **options):
        for supplied_data in models.SuppliedData.objects.filter(
            expired=False, created__lt=timezone.now() - datetime.timedelta(days=settings.DELETE_FILES_AFTER_DAYS)
        ):
            supplied_data.expired = datetime.datetime.now(tz=datetime.timezone.UTC)
            supplied_data.save()
            try:
                shutil.rmtree(supplied_data.upload_dir())
            except FileNotFoundError:
                continue
