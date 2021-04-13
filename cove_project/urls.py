from cove.urls import handler500  # noqa: F401
from cove.urls import urlpatterns as urlpatterns_core
from django.conf import settings
from django.conf.urls import include, re_path
from django.conf.urls.static import static
from django.views.generic import RedirectView

import cove_ocds.views

# Serve the OCDS validator at /validator/
urlpatterns_core += [re_path(r"^data/(.+)$", cove_ocds.views.explore_ocds, name="explore")]

urlpatterns = [
    re_path(r"^$", RedirectView.as_view(url="review/", permanent=False)),
    re_path("^review/", include(urlpatterns_core)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
