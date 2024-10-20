from django.conf import settings


def from_settings(_request):
    return {
        "fathom": settings.FATHOM,
        "support_email": settings.SUPPORT_EMAIL,
        "delete_files_after_days": getattr(settings, "DELETE_FILES_AFTER_DAYS", 7),
    }
