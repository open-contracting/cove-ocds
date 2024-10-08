from django.conf import settings


def from_settings(_request):
    return {
        "fathom": settings.FATHOM,
        "hotjar": settings.HOTJAR,
        "releases_or_records_table_length": settings.RELEASES_OR_RECORDS_TABLE_LENGTH,
        "releases_or_records_table_slice": f":{settings.RELEASES_OR_RECORDS_TABLE_LENGTH}",
    }
