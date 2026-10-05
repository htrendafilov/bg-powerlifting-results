import uuid
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from archive.forms import ImportForm, RecordFilterForm
from archive.models import (
    AgeGroup,
    Athlete,
    Competition,
    Equipment,
    Event,
    FileKind,
    Lift,
    MeetLevel,
    Record,
    RecordOrigin,
    Result,
    Sex,
)
from archive.services.commit import (
    ReplaceScopeError, apply_import, decimal_or_blank, matching_source, prepare_rows, rows_to_replace,
)
from archive.services.importers import parse_upload
from archive.services.namesakes import career_hints, namesakes_of, shared_names
from archive.search import match_athlete_name
from archive.services.visibility import (
    visible_athletes,
    visible_competitions,
    visible_records,
    visible_results,
)

SESSION_KEY = "protocol_import"
ATHLETES_PER_PAGE = 100

CLASS_LISTS = {
    (Sex.M, AgeGroup.SUBJUNIOR): ["53", "59", "66", "74", "83", "93", "105", "120", "120+"],
    (Sex.F, AgeGroup.SUBJUNIOR): ["43", "47", "52", "57", "63", "69", "76", "84", "84+"],
    (Sex.M, AgeGroup.OPEN): ["59", "66", "74", "83", "93", "105", "120", "120+"],
    (Sex.F, AgeGroup.OPEN): ["47", "52", "57", "63", "69", "76", "84", "84+"],
}


def home(request):
    competitions = visible_competitions(
        Competition.objects.annotate(file_count=Count("files"))
    ).order_by("-start_date", "name")[:8]
    return render(
        request,
        "archive/home.html",
        {
            "competitions": competitions,
            "athlete_count": visible_athletes(Athlete.objects.all()).count(),
            "result_count": visible_results().count(),
        },
    )


def competition_list(request):
    level = request.GET.get("level", "")
    competitions = visible_competitions(Competition.objects.annotate(file_count=Count("files")))
    if level in MeetLevel.values:
        competitions = competitions.filter(level=level)
    competitions = competitions.order_by("-start_date", "name")
    by_year = []
    for competition in competitions:
        year = competition.start_date.year
        if not by_year or by_year[-1]["year"] != year:
            by_year.append({"year": year, "competitions": []})
        by_year[-1]["competitions"].append(competition)
    return render(
        request,
        "archive/competition_list.html",
        {"by_year": by_year, "levels": MeetLevel, "selected_level": level},
    )


def competition_detail(request, slug):
    competition = get_object_or_404(visible_competitions(Competition.objects.all()), slug=slug)
    files = list(competition.files.all())
    has_any_results = visible_results(competition.results.all()).exists()
    results = visible_results(competition.results.select_related("athlete"))
    sex = request.GET.get("sex", "")
    age_group = request.GET.get("age", "")
    equipment = request.GET.get("equipment", "")
    event = request.GET.get("event", "")
    if sex in Sex.values:
        results = results.filter(sex=sex)
    if age_group in AgeGroup.values:
        results = results.filter(age_group=age_group)
    if equipment in Equipment.values:
        results = results.filter(equipment=equipment)
    if event in Event.values:
        results = results.filter(event=event)
    results = list(results)
    return render(
        request,
        "archive/competition_detail.html",
        {
            "competition": competition,
            "results": results,
            "groups": _group_results(results),
            "scans": [f for f in files if f.kind == FileKind.SCAN and f.file],
            # The federation's own link is the protocol; a file uploaded here is
            # the same bytes kept where they cannot vanish, so it is shown as a
            # copy — unless there is no link, when it is all the archive has.
            "protocols": _protocols(files),
            "copies": _local_copies(files),
            "sources": [f for f in files if f.kind == FileKind.OPL and f.url],
            **_visible_columns(results),
            "has_any_results": has_any_results,
            "filters": {
                "sex": Sex,
                "age": AgeGroup,
                "equipment": Equipment,
                "event": Event,
                "selected_sex": sex,
                "selected_age": age_group,
                "selected_equipment": equipment,
                "selected_event": event,
            },
        },
    )


def records(request):
    form = RecordFilterForm(request.GET or None)
    if form.is_valid():
        selected = form.cleaned_data
    else:
        selected = {
            "sex": Sex.M,
            "age_group": AgeGroup.OPEN,
            "equipment": Equipment.CLASSIC,
            "event": Event.SBD,
        }
        form = RecordFilterForm(initial=selected)
    lifts = [Lift.BENCH] if selected["event"] == Event.B else [Lift.SQUAT, Lift.BENCH, Lift.DEADLIFT, Lift.TOTAL]
    classes = _classes_for(selected)
    current = {}
    for record in visible_records(Record.objects.select_related("athlete")).filter(
        sex=selected["sex"],
        age_group=selected["age_group"],
        equipment=selected["equipment"],
        event=selected["event"],
        valid_to=None,
    ):
        key = (record.weight_class, record.lift)
        existing = current.get(key)
        if existing is None or existing.origin == RecordOrigin.STANDARD:
            current[key] = record
    lift_headers = [{"value": lift, "label": label} for lift, label in Lift.choices if lift in lifts]
    rows = []
    for weight_class in classes:
        cells = []
        for lift in lift_headers:
            record = current.get((weight_class, lift["value"]))
            cells.append({"lift": lift, "record": record})
        rows.append({"weight_class": weight_class, "cells": cells})
    return render(
        request,
        "archive/records.html",
        {"form": form, "rows": rows, "lifts": lift_headers, "selected": selected},
    )


def record_history(request):
    fields = ("sex", "age_group", "equipment", "event", "lift", "weight_class")
    filters = {field: request.GET.get(field, "") for field in fields}
    history = visible_records(Record.objects.select_related("athlete", "result__competition")).filter(
        **filters,
        origin__in=[RecordOrigin.SEED, RecordOrigin.RESULT],
    )
    standard = Record.objects.filter(**filters, origin=RecordOrigin.STANDARD).first()
    return render(
        request,
        "archive/record_history.html",
        {"history": history, "standard": standard, "filters": filters},
    )


def athlete_list(request):
    query = request.GET.get("q", "").strip()
    athletes = visible_athletes(Athlete.objects.all())
    if query:
        athletes = match_athlete_name(athletes, query)
    page = Paginator(athletes, ATHLETES_PER_PAGE).get_page(request.GET.get("page"))
    shared = shared_names()
    hints = career_hints([a for a in page if a.display_name in shared])
    for athlete in page:
        athlete.hint = hints.get(athlete.pk, "")
    return render(
        request,
        "archive/athlete_list.html",
        {
            "page": page,
            "page_range": page.paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1),
            "query": query,
        },
    )


def athlete_detail(request, slug):
    athlete = get_object_or_404(visible_athletes(Athlete.objects.all()), slug=slug)
    results = visible_results(
        athlete.results.select_related("competition")
    ).order_by("-competition__start_date")
    photos = athlete.photos.all() if athlete.allows_public_photos else []
    namesakes = namesakes_of(athlete)
    hints = career_hints([athlete, *namesakes]) if namesakes else {}
    for person in [athlete, *namesakes]:
        person.hint = hints.get(person.pk, "")
    return render(
        request,
        "archive/athlete_detail.html",
        {"athlete": athlete, "results": results, "photos": photos, "namesakes": namesakes},
    )


@staff_member_required
def import_meet(request):
    form = ImportForm()
    if request.method == "POST":
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.cleaned_data["upload"]
            payload = upload.read()
            parsed = parse_upload(upload.name, payload)
            if not parsed.rows:
                form.add_error("upload", " ".join(parsed.errors) or "Файлът няма редове за внасяне.")
            else:
                token = uuid.uuid4().hex
                path = default_storage.save(f"imports/{token}-{_safe_name(upload.name)}", ContentFile(payload))
                options = _options_from_form(form.cleaned_data, path, upload.name, parsed)
                request.session[SESSION_KEY] = options
                ready, blocked = prepare_rows(parsed, **_prepare_kwargs(options))
                return render(
                    request,
                    "archive/import_preview.html",
                    {"parsed": parsed, "ready": ready, "blocked": blocked, "options": options,
                     "kg": decimal_or_blank, **_replacement(options)},
                )
    return render(request, "archive/import_form.html", {"form": form})


@staff_member_required
@require_POST
def import_confirm(request):
    options = request.session.get(SESSION_KEY)
    if not options or not default_storage.exists(options["path"]):
        messages.error(request, "Импортът е изтекъл. Качи файла отново.")
        return redirect("import_meet")
    with default_storage.open(options["path"], "rb") as handle:
        payload = handle.read()
    parsed = parse_upload(options["filename"], payload)
    ready, blocked = prepare_rows(parsed, **_prepare_kwargs(options))
    scope = _replacement(options)
    if blocked or not ready or scope["scope_error"]:
        return render(
            request,
            "archive/import_preview.html",
            {"parsed": parsed, "ready": ready, "blocked": blocked, "options": options,
             "kg": decimal_or_blank, **scope},
        )
    if not options["competition_id"] and not options["start_date"] and not parsed.meet_date:
        messages.error(request, "Файлът няма дата. Попълни я във формата.")
        return redirect("import_meet")
    competition = _competition_from_options(options, parsed)
    with default_storage.open(options["path"], "rb") as handle:
        summary = apply_import(
            competition,
            parsed,
            default_sex=options["default_sex"],
            default_equipment=options["default_equipment"],
            default_event=options["default_event"],
            replace=options["replace"],
            stored_file=handle,
            filename=options["filename"],
        )
    request.session.pop(SESSION_KEY, None)
    messages.success(request, f"Внесени са {summary['created']} реда. Нови състезатели: {summary['athletes']}.")
    return redirect("competition_detail", slug=competition.slug)


def _options_from_form(cleaned, path, filename, parsed):
    competition = cleaned.get("competition")
    # The preview must judge the rows by the same date the import will use.
    if competition:
        start = competition.start_date
    else:
        start = cleaned.get("start_date") or parsed.meet_date
    return {
        "path": path,
        "filename": filename,
        "competition_id": competition.pk if competition else None,
        "name": cleaned.get("name") or parsed.title or filename,
        "start_date": start.isoformat() if start else "",
        "city": cleaned.get("city") or parsed.city,
        "level": competition.level if competition else (cleaned.get("level") or MeetLevel.NATIONAL),
        "default_sex": cleaned.get("default_sex") or "",
        "default_equipment": cleaned.get("default_equipment") or "auto",
        "default_event": cleaned.get("default_event") or "auto",
        "replace": cleaned.get("replace") or "file",
    }


def _replacement(options):
    if not options["competition_id"]:
        return {"replaced": 0, "scope_error": ""}
    competition = Competition.objects.get(pk=options["competition_id"])
    source = matching_source(competition, options["filename"])
    try:
        doomed = rows_to_replace(competition, source, options["replace"], keeps_file=True)
    except ReplaceScopeError as error:
        return {"replaced": 0, "scope_error": str(error)}
    return {"replaced": doomed.count(), "scope_error": ""}


def _prepare_kwargs(options):
    return {
        "default_sex": options["default_sex"],
        "default_equipment": options["default_equipment"],
        "default_event": options["default_event"],
        "meet_level": options["level"],
        "meet_date": date.fromisoformat(options["start_date"]) if options["start_date"] else None,
    }


def _competition_from_options(options, parsed):
    if options["competition_id"]:
        return Competition.objects.get(pk=options["competition_id"])
    start = date.fromisoformat(options["start_date"] or parsed.meet_date.isoformat())
    return Competition.objects.create(
        name=options["name"],
        start_date=start,
        city=options["city"],
        level=options["level"],
    )


# Sex first, then weight class, the way a protocol is read. Age group and
# equipment stay as columns rather than further nesting, so one class block
# holds every division that lifted in it.
def _protocols(files):
    kept = [f for f in files if f.kind != FileKind.OPL]
    linked = [f for f in kept if f.url]
    return linked or [f for f in kept if f.file]


def _local_copies(files):
    kept = [f for f in files if f.kind != FileKind.OPL]
    if not any(f.url for f in kept):
        return []
    return [f for f in kept if f.file]


def _visible_columns(results):
    def used(best, first):
        return any(getattr(r, best) or getattr(r, first) for r in results)

    columns = {
        "show_squat": used("best_squat", "squat1"),
        "show_bench": used("best_bench", "bench1"),
        "show_deadlift": used("best_deadlift", "deadlift1"),
        "show_total": any(r.total for r in results),
    }
    width = 7  # place, name, club, age, equipment, bodyweight, points
    width += 3 * sum(columns[key] for key in ("show_squat", "show_bench", "show_deadlift"))
    width += 1 if columns["show_total"] else 0
    return {**columns, "column_count": width}


def _group_results(results):
    order = {Sex.F: 0, Sex.M: 1}
    age_order = {value: index for index, value in enumerate(AgeGroup.values)}
    ordered = sorted(
        results,
        key=lambda r: (
            order.get(r.sex, 9),
            _class_key(r.weight_class),
            age_order.get(r.age_group, 99),
            _place_key(r.place),
        ),
    )
    groups = []
    for result in ordered:
        if not groups or groups[-1]["sex"] != result.sex:
            groups.append({"sex": result.sex, "label": dict(Sex.choices).get(result.sex, "—"), "classes": []})
        classes = groups[-1]["classes"]
        if not classes or classes[-1]["weight_class"] != result.weight_class:
            classes.append({"weight_class": result.weight_class, "results": []})
        classes[-1]["results"].append(result)
    return groups


def _place_key(value):
    text = (value or "").strip().upper()
    try:
        return (0, int(text))
    except ValueError:
        return (1, 0) if text else (2, 0)


def _classes_for(selected):
    preset = CLASS_LISTS.get((selected["sex"], selected["age_group"]))
    if preset is None:
        preset = CLASS_LISTS[(selected["sex"], AgeGroup.OPEN)]
    extras = visible_records(Record.objects.all()).filter(
        sex=selected["sex"],
        age_group=selected["age_group"],
        equipment=selected["equipment"],
        event=selected["event"],
    ).values_list("weight_class", flat=True)
    classes = list(dict.fromkeys([*preset, *extras]))
    return sorted(classes, key=_class_key)


def _class_key(value):
    plus = str(value).endswith("+")
    try:
        number = Decimal(str(value).rstrip("+"))
    except Exception:
        return (Decimal("9999"), True, str(value))
    return (number, plus, "")


def _safe_name(filename):
    return "".join(char if char.isalnum() or char in ".-_" else "-" for char in filename)[-80:]
