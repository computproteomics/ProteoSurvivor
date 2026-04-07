from pathlib import Path

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]

# In the combined single-container setup Django also serves the React SPA.
# The built index.html is discovered via TEMPLATES[0]["DIRS"] (set in the
# combined settings module).  We add the catch-all only when that directory
# is configured so that the development / split-container setups are unaffected.
_frontend_dirs = [Path(d) for d in settings.TEMPLATES[0].get("DIRS", [])]
if _frontend_dirs and any((d / "index.html").exists() for d in _frontend_dirs):
    urlpatterns += [
        re_path(
            r"^(?!api/|admin/|static/).*$",
            TemplateView.as_view(template_name="index.html"),
        ),
    ]
