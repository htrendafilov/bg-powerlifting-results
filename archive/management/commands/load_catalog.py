from datetime import date

from django.core.management.base import BaseCommand

from archive.catalog import CATALOG
from archive.models import Competition, CompetitionFile, FileKind, MeetLevel


class Command(BaseCommand):
    help = "Създава националните състезания от 2021 насам, включително тези без протокол."

    def handle(self, *args, **options):
        created = 0
        for item in CATALOG:
            competition, was_created = Competition.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "start_date": item["start"],
                    "end_date": item.get("end"),
                    "city": item["city"],
                    "country": "България",
                    "level": MeetLevel.NATIONAL,
                },
            )
            created += int(was_created)
            for title, url in item["links"]:
                CompetitionFile.objects.get_or_create(
                    competition=competition,
                    url=url,
                    defaults={"kind": FileKind.LINK, "title": title},
                )
        missing = Competition.objects.filter(files__isnull=True, start_date__lte=date.today()).count()
        self.stdout.write(f"Състезания в списъка: {len(CATALOG)}. Нови: {created}. Без протокол до днес: {missing}.")
