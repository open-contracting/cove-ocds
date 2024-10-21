from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, re_path

import cove_ocds.views

urlpatterns = [
    re_path(r"^$", cove_ocds.views.data_input, name="index"),
    re_path(r"^data/(.+)$", cove_ocds.views.explore_ocds, name="explore"),
    re_path(r"^i18n/", include("django.conf.urls.i18n")),
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]
