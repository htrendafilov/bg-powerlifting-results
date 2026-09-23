"""Turn names a protocol wrote in capitals back into ordinary names.

The Kardzhali 2023 protocol is typed in capitals, and transliterating those
produced "VENTsISLAV" because the digraph for Ц was capitalised as a word. A
Latin name that was derived from the Cyrillic one is rebuilt from the corrected
spelling; one that came from a source of its own is only recased.
"""

from django.core.management.base import BaseCommand

from archive.models import Athlete
from archive.services.names import normalize_name, transliterate


class Command(BaseCommand):
    help = "Оправя имената, записани изцяло с главни букви."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        changed = 0
        for athlete in Athlete.objects.all():
            name_bg = normalize_name(athlete.name_bg)
            name_lat = athlete.name_lat
            if name_bg != athlete.name_bg:
                # Rebuild the Latin spelling only when it came from this name.
                # Compared without case because the old transliteration wrote
                # the digraphs as "Ts" inside a word in capitals.
                if name_lat.upper() == transliterate(athlete.name_bg).upper():
                    name_lat = transliterate(name_bg)
            name_lat = normalize_name(name_lat)
            if (name_bg, name_lat) == (athlete.name_bg, athlete.name_lat):
                continue
            self.stdout.write(
                f"  {athlete.name_bg or athlete.name_lat!r} -> {name_bg or name_lat!r}"
                f"   ({athlete.name_lat!r} -> {name_lat!r})"
            )
            changed += 1
            if not options["dry_run"]:
                athlete.name_bg, athlete.name_lat = name_bg, name_lat
                athlete.save()
        self.stdout.write(f"поправени: {changed}")
        if options["dry_run"]:
            self.stdout.write("СУХ ПРОБЕГ, нищо не е записано.")
