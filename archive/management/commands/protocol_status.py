"""Where every meet in the archive stands: entered, waiting, or with no protocol.

Written out as review/protocols.md so the list is in the repository, and
generated from the database so it cannot drift from what is actually loaded.
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.db.models import Count

from archive.models import Competition, MeetLevel

# Why a meet that has a protocol is still not entered. Kept here rather than in
# the generated file so the file stays a report.
NOTES = {
    "2020-dupnitsa-leg": "Няма протокол. Търси се.",
    "2020-sofia-sbd": "Няма протокол. Търси се.",
    "2021-dupnitsa-krag-1": "ZIP с 15 снимки на хартиен протокол. Ръчно въвеждане.",
    "2021-dupnitsa-leg": "ZIP със 7 снимки на хартиен протокол. Ръчно въвеждане.",
    "2021-haskovo-krag-3": "ZIP с 11 снимки на хартиен протокол. Ръчно въвеждане.",
    "2022-haskovo-leg": "Резултатите са от OpenPowerlifting. Протоколът на федерацията не се чете.",
    "2022-haskovo-kupa-anton-kolev": "Няма протокол. Търси се.",
    "2022-dupnitsa-ekip": "Чете се, но без пол, възраст и екипировка по редове.",
    "2022-gorna-oryahovitsa-classic": "Чете се, но без възрастови групи.",
    "2023-sofia-leg": "Три файла в стар .xls формат. Иска конверсия.",
    "2023-dupnitsa-classic": "Резултатите са от OpenPowerlifting. Протокол няма.",
    "2023-haskovo-leg": "Няма протокол. Търси се.",
    "2024-pernik-ekip": "Резултатите са от OpenPowerlifting. Протоколът е само PDF.",
    "2024-sofia-leg-may": "Няма протокол. Търси се.",
    "2024-dupnitsa-leg": "Резултатите са от OpenPowerlifting. Протоколът на федерацията не се чете.",
    "2025-dupnitsa-youth": "Ръчна таблица без заглавен ред. Иска свой четец.",
    "2025-kardzhali-classic": "Чете се, но няма колона за пол.",
}


class Command(BaseCommand):
    help = "Показва състоянието на протоколите и записва review/protocols.md."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true", help="записва review/protocols.md")

    def handle(self, *args, **options):
        rows = (
            Competition.objects.filter(level=MeetLevel.NATIONAL)
            .annotate(file_total=Count("files", distinct=True), result_total=Count("results", distinct=True))
            .order_by("-start_date")
        )
        lines = [
            "# Състояние на протоколите",
            "",
            "Само националните състезания. Международните идват от OpenPowerlifting и се",
            "обновяват с `manage.py import_opl`.",
            "",
            f"Генериран с `manage.py protocol_status --write` на {date.today():%d.%m.%Y}.",
            "Не се редактира на ръка — бележките са в самата команда.",
            "",
            "| Дата | Състезание | Град | Файлове | Редове | Състояние | Бележка |",
            "|---|---|---|---|---|---|---|",
        ]
        totals = {"готови": 0, "чакат": 0, "без протокол": 0, "предстои": 0}
        for meet in rows:
            state, bucket = self._state(meet)
            totals[bucket] += 1
            note = NOTES.get(meet.slug, "")
            lines.append(
                f"| {meet.start_date:%d.%m.%Y} | {meet.name} | {meet.city} | "
                f"{meet.file_total or '–'} | {meet.result_total or '–'} | {state} | {note} |"
            )
        lines += [
            "",
            f"**Въведени: {totals['готови']} · чакат: {totals['чакат']} · "
            f"без протокол: {totals['без протокол']} · предстоящи: {totals['предстои']}**",
            "",
        ]
        text = "\n".join(lines)
        self.stdout.write(text)
        if options["write"]:
            from pathlib import Path

            path = Path("review/protocols.md")
            path.parent.mkdir(exist_ok=True)
            path.write_text(text, encoding="utf-8")
            self.stdout.write(f"\nзаписан: {path}")

    def _state(self, meet):
        if meet.result_total:
            return "✅ въведено", "готови"
        if meet.start_date > date.today():
            return "🕓 предстои", "предстои"
        if meet.file_total:
            return "📄 има протокол", "чакат"
        return "⛔ няма протокол", "без протокол"
