from django.contrib import admin

from archive.models import Athlete, AthletePhoto, Competition, CompetitionFile, Record, Result


class PhotoInline(admin.TabularInline):
    model = AthletePhoto
    extra = 0


class FileInline(admin.TabularInline):
    model = CompetitionFile
    extra = 0


@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    list_display = ("display_name", "sex", "birth_year", "adult_confirmed", "name_lat")
    list_filter = ("sex", "adult_confirmed")
    search_fields = ("name_bg", "name_lat")
    inlines = [PhotoInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["slug"].required = False
        return form


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "city", "level")
    list_filter = ("level", "start_date")
    search_fields = ("name", "city")
    inlines = [FileInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["slug"].required = False
        return form


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = (
        "raw_name",
        "competition",
        "sex",
        "age_group",
        "equipment",
        "event",
        "weight_class",
        "total",
        "best_bench",
        "place",
        "review_note",
    )
    list_filter = ("event", "equipment", "age_group", "sex", "competition")
    search_fields = ("raw_name", "athlete__name_bg", "athlete__name_lat", "club")
    autocomplete_fields = ("athlete", "competition")


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = (
        "sex",
        "age_group",
        "equipment",
        "event",
        "lift",
        "weight_class",
        "value_kg",
        "athlete",
        "origin",
        "valid_from",
        "valid_to",
    )
    list_filter = ("origin", "sex", "age_group", "equipment", "event", "lift")
    search_fields = ("athlete__name_bg", "athlete__name_lat", "note", "weight_class")
    autocomplete_fields = ("athlete", "result")
