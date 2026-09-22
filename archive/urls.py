from django.urls import path

from archive import views

urlpatterns = [
    path("", views.home, name="home"),
    path("competitions/", views.competition_list, name="competition_list"),
    path("competitions/<slug:slug>/", views.competition_detail, name="competition_detail"),
    path("records/", views.records, name="records"),
    path("records/history/", views.record_history, name="record_history"),
    path("athletes/", views.athlete_list, name="athlete_list"),
    path("athletes/<slug:slug>/", views.athlete_detail, name="athlete_detail"),
    path("import/", views.import_meet, name="import_meet"),
    path("import/confirm/", views.import_confirm, name="import_confirm"),
]
