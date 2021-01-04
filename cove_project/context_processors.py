from django.conf import settings


def from_settings(request):
    return {
        'hotjar': settings.HOTJAR,
        'releases_or_records_table_length': settings.RELEASES_OR_RECORDS_TABLE_LENGTH,
        'releases_or_records_table_slice': ":{}".format(settings.RELEASES_OR_RECORDS_TABLE_LENGTH),
    }
