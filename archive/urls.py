from django.urls import path

from archive import views

urlpatterns = [
    path("", views.home, name="home"),
    path("sustezaniya/", views.competition_list, name="competition_list"),
    path("sustezaniya/<slug:slug>/", views.competition_detail, name="competition_detail"),
    path("rekordi/", views.records, name="records"),
    path("rekordi/istoria/", views.record_history, name="record_history"),
    path("sastezateli/", views.athlete_list, name="athlete_list"),
    path("sastezateli/<slug:slug>/", views.athlete_detail, name="athlete_detail"),
    path("import/", views.import_meet, name="import_meet"),
    path("import/potvardi/", views.import_confirm, name="import_confirm"),
]
