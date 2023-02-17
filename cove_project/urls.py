from cove.urls import handler500  # noqa: F401
from cove.urls import urlpatterns
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path

import cove_ocds.views

urlpatterns += [re_path(r"^data/(.+)$", cove_ocds.views.explore_ocds, name="explore")]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
