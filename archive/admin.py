from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count, Max, Min
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from archive.models import (
    Athlete,
    AthletePhoto,
    Competition,
    CompetitionFile,
    Record,
    Result,
    SiteSettings,
)
from archive.services.merge import duplicate_candidates, merge_athletes
from archive.services.records import recalculate_records


class PhotoInline(admin.TabularInline):
    model = AthletePhoto
    extra = 0


class StartInline(admin.TabularInline):
    """The starts, for reading. Editing one is done from Резултати."""

    model = Result
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name_plural = "Стартове"
    fields = ("meet", "weight_class", "age_group", "equipment", "event", "place", "total", "best_bench")
    readonly_fields = fields
    ordering = ("competition__start_date",)

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Състезание")
    def meet(self, obj):
        return f"{obj.competition.start_date:%d.%m.%Y}  {obj.competition.name}"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("competition")


class FileInline(admin.TabularInline):
    model = CompetitionFile
    extra = 0


@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    list_display = ("display_name", "needs_check", "sex", "birth_year", "start_count", "years", "name_lat")
    list_filter = ("name_bg_auto", "sex", "adult_confirmed")
    search_fields = ("name_bg", "name_lat")
    inlines = [StartInline, PhotoInline]
    actions = ["merge_selected"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            starts_total=Count("results"),
            first_start=Min("results__competition__start_date"),
            last_start=Max("results__competition__start_date"),
        )

    @admin.display(description="Име за проверка", boolean=True, ordering="name_bg_auto")
    def needs_check(self, obj):
        return obj.name_bg_auto

    @admin.display(description="Стартове", ordering="starts_total")
    def start_count(self, obj):
        return obj.starts_total

    @admin.display(description="Години")
    def years(self, obj):
        if not obj.first_start:
            return "–"
        if obj.first_start.year == obj.last_start.year:
            return obj.first_start.year
        return f"{obj.first_start.year}–{obj.last_start.year}"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["slug"].required = False
        return form

    def get_urls(self):
        extra = [
            path(
                "duplicates/",
                self.admin_site.admin_view(self.duplicates_view),
                name="archive_athlete_duplicates",
            )
        ]
        return extra + super().get_urls()

    @admin.action(description="Слей избраните състезатели")
    def merge_selected(self, request, queryset):
        athletes = list(queryset.order_by("-starts_total", "pk"))
        if len(athletes) < 2:
            self.message_user(request, "Избери поне двама.", level=messages.WARNING)
            return None
        if request.POST.get("confirm_merge"):
            target = next((a for a in athletes if str(a.pk) == request.POST.get("target")), None)
            if target is None:
                self.message_user(request, "Не е избран кой запис остава.", level=messages.WARNING)
                return None
            others = [a for a in athletes if a.pk != target.pk]
            absorbed = merge_athletes(target, others)
            self.message_user(
                request,
                f"{target.display_name}: слети {len(absorbed)} — {', '.join(absorbed)}.",
            )
            return redirect(reverse("admin:archive_athlete_changelist"))
        return render(
            request,
            "admin/archive/athlete/merge.html",
            {
                **self.admin_site.each_context(request),
                "title": "Сливане на състезатели",
                "athletes": athletes,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
            },
        )

    @staticmethod
    def _starts(athlete):
        return list(
            athlete.results.select_related("competition").order_by("competition__start_date")
        )

    def _pair(self, score, one, two):
        left, right = self._starts(one), self._starts(two)
        shared = {r.competition_id for r in left} & {r.competition_id for r in right}
        return {
            "score": round(score * 100),
            "one": one,
            "two": two,
            "one_rows": left,
            "two_rows": right,
            # Two lifters at the same meet are two people, whatever the names say.
            "shared": [r.competition for r in left if r.competition_id in shared][:1],
        }

    def duplicates_view(self, request):
        pairs = duplicate_candidates()
        return render(
            request,
            "admin/archive/athlete/duplicates.html",
            {
                **self.admin_site.each_context(request),
                "title": "Възможни дубликати",
                "pairs": [self._pair(score, one, two) for score, one, two in pairs],
            },
        )


class RecalculatesRecords:
    """Records are derived from results, so any edit that can move one has to
    rebuild them, after the change is committed."""

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        transaction.on_commit(recalculate_records)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        transaction.on_commit(recalculate_records)

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        transaction.on_commit(recalculate_records)


@admin.register(Competition)
class CompetitionAdmin(RecalculatesRecords, admin.ModelAdmin):
    list_display = ("name", "start_date", "city", "level")
    list_filter = ("level", "start_date")
    search_fields = ("name", "city")
    inlines = [FileInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["slug"].required = False
        return form


@admin.register(Result)
class ResultAdmin(RecalculatesRecords, admin.ModelAdmin):
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


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """A single row, so adding and deleting are off."""

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        SiteSettings.load()
        return super().changelist_view(request, extra_context)
