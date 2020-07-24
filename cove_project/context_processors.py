from django.conf import settings


def from_settings(request):
    return {
        'hotjar': settings.HOTJAR,
        'releases_table_length': settings.RELEASES_TABLE_LENGTH,
        'releases_table_slice': ":{}".format(settings.RELEASES_TABLE_LENGTH),
    }
