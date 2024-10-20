# https://github.com/OpenDataServices/lib-cove-web/blob/main/cove/input/models.py

import os
import secrets
import string
import uuid
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from werkzeug.http import parse_options_header

CONTENT_TYPE_MAP = {
    "application/json": "json",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/csv": "csv",
    "application/vnd.oasis.opendocument.spreadsheet": "ods",
    "application/xml": "xml",
    "text/xml": "xml",
}

ALPHABET = f"{string.ascii_letters}{string.digits}"


def upload_to(instance, filename=""):
    return os.path.join(str(instance.pk), "".join(secrets.choice(ALPHABET) for i in range(16)), filename)


class SuppliedData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # URLField limits schemes to http, https, ftp, ftps by default.
    # https://docs.djangoproject.com/en/5.1/ref/validators/#django.core.validators.URLValidator.schemes
    source_url = models.URLField(blank=True, max_length=2000)
    original_file = models.FileField(upload_to=upload_to, max_length=256)
    created = models.DateTimeField(auto_now_add=True, null=True)
    expired = models.BooleanField(default=False)

    class Meta:
        db_table = "input_supplieddata"

    def __str__(self):
        return f"<SuppliedData source_url={self.source_url!r} original_file.name={self.original_file.name!r}>"

    def upload_dir(self):
        return os.path.join(settings.MEDIA_ROOT, str(self.pk), "")

    def upload_url(self):
        return os.path.join(settings.MEDIA_URL, str(self.pk), "")

    def download(self):
        response = requests.get(
            self.source_url,
            headers={"User-Agent": settings.USER_AGENT},
            timeout=settings.REQUESTS_TIMEOUT,
        )
        response.raise_for_status()

        file_extension = CONTENT_TYPE_MAP.get(response.headers.get("content-type", "").split(";", 1)[0].lower())
        if not file_extension:
            _, options = parse_options_header(response.headers.get("content-disposition"))
            if "filename*" in options:
                filename = options["filename*"]
            elif "filename" in options:
                filename = options["filename"]
            else:
                filename = urlsplit(response.url).path.rstrip("/").rsplit("/", 1)[-1]
            possible_extension = filename.rsplit(".", 1)[-1]
            if possible_extension in CONTENT_TYPE_MAP.values():
                file_extension = possible_extension

        file_name = response.url.split("/", -1)[-1].split("?", 1)[0][:100] or "file"
        if file_extension and not file_name.endswith(file_extension):
            file_name = f"{file_name}.{file_extension}"

        self.original_file.save(file_name, ContentFile(response.content))
