# linkedin/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from linkedin.views import landing_page

urlpatterns = [
    path("", landing_page),
    path("crm/", include("crm.urls")),
    path("crm/", include("common.urls")),
    path("admin/", admin.site.urls),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
