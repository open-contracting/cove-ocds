from cove.urls import handler500  # noqa: F401
from cove.urls import urlpatterns as urlpatterns_core
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from django.views.generic import RedirectView

import cove_ocds.views

urlpatterns_core += [re_path(r"^data/(.+)$", cove_ocds.views.explore_ocds, name="explore")]

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="index", permanent=False)),
    path(settings.URL_PREFIX, include(urlpatterns_core)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
