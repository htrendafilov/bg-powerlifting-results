from archive.models import AGE_RECORD_GROUPS, Event, Lift, Record, RecordOrigin, Result


# The one note this pass writes, and so the only one it may clear; anything
# else in review_note was typed by an editor.
EARLIER_THAN_SEED = "По-висок от записания рекорд, но с по-ранна дата."


def recalculate_records():
    Result.objects.filter(review_note=EARLIER_THAN_SEED).update(review_note="")
    Record.objects.filter(origin=RecordOrigin.RESULT).delete()
    Record.objects.filter(origin=RecordOrigin.SEED).update(valid_to=None)

    current = {}
    for record in Record.objects.filter(origin=RecordOrigin.SEED, valid_to=None).order_by("value_kg", "id"):
        current[_key(record)] = record
    standards = {
        _key(record): record.value_kg
        for record in Record.objects.filter(origin=RecordOrigin.STANDARD)
    }

    results = (
        Result.objects.select_related("competition", "athlete")
        .order_by("competition__start_date", "id")
    )
    for result in results:
        if not result.counts_for_bulgarian_records:
            continue
        for age_group, lift, value, event in _candidates(result):
            key = (result.sex, age_group, result.equipment, event, lift, result.weight_class)
            holder = current.get(key)
            if holder is None:
                standard = standards.get(key)
                if standard is not None and value <= standard:
                    continue
                current[key] = _open_record(result, age_group, lift, event, value)
                continue
            if value < holder.value_kg:
                continue
            if value == holder.value_kg:
                _link_same_mark(holder, result)
                continue
            if (
                holder.origin == RecordOrigin.SEED
                and holder.valid_from
                and result.competition.start_date < holder.valid_from
            ):
                if not result.review_note:
                    result.review_note = EARLIER_THAN_SEED
                    result.save(update_fields=["review_note"])
                continue
            holder.valid_to = result.competition.start_date
            holder.save(update_fields=["valid_to"])
            current[key] = _open_record(result, age_group, lift, event, value)


def _candidates(result):
    groups = AGE_RECORD_GROUPS.get(result.age_group, [result.age_group])
    if result.event == Event.B:
        lifts = [(Lift.BENCH, result.lift_value(Lift.BENCH), Event.B)]
    else:
        lifts = [
            (Lift.SQUAT, result.lift_value(Lift.SQUAT), Event.SBD),
            (Lift.BENCH, result.lift_value(Lift.BENCH), Event.SBD),
            (Lift.DEADLIFT, result.lift_value(Lift.DEADLIFT), Event.SBD),
            (Lift.TOTAL, result.lift_value(Lift.TOTAL), Event.SBD),
        ]
    for age_group in groups:
        for lift, value, event in lifts:
            if value is None or not result.weight_class:
                continue
            yield age_group, lift, value, event


def _key(record):
    return (record.sex, record.age_group, record.equipment, record.event, record.lift, record.weight_class)


def _open_record(result, age_group, lift, event, value):
    return Record.objects.create(
        sex=result.sex,
        age_group=age_group,
        equipment=result.equipment,
        event=event,
        lift=lift,
        weight_class=result.weight_class,
        value_kg=value,
        athlete=result.athlete,
        result=result,
        origin=RecordOrigin.RESULT,
        valid_from=result.competition.start_date,
    )


def _link_same_mark(holder, result):
    if holder.result_id or holder.athlete_id != result.athlete_id:
        return
    holder.result = result
    holder.save(update_fields=["result"])
