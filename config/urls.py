from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.views.i18n import JavaScriptCatalog

admin.site.site_header = "Архив силов трибой"
admin.site.site_title = "Архив силов трибой"

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
]

# The site first shipped with transliterated paths. Kept as temporary
# redirects rather than 301s so the English names can still be reconsidered.
_MOVED = [
    ("sustezaniya/", "competition_list"),
    ("sustezaniya/<slug:slug>/", "competition_detail"),
    ("rekordi/", "records"),
    ("rekordi/istoria/", "record_history"),
    ("sastezateli/", "athlete_list"),
    ("sastezateli/<slug:slug>/", "athlete_detail"),
    ("import/potvardi/", "import_confirm"),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    *[
        path(route, RedirectView.as_view(pattern_name=name, query_string=True))
        for route, name in _MOVED
    ],
    path("", include("archive.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
