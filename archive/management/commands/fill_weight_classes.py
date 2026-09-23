from django.core.management.base import BaseCommand

from archive.models import Result
from archive.services.records import recalculate_records
from archive.services.weight_classes import weight_class_for


class Command(BaseCommand):
    help = "Попълва липсващите тегловни категории от личното тегло."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        rows = Result.objects.filter(weight_class="").exclude(bodyweight=None).select_related(
            "competition"
        )
        filled = 0
        for result in rows:
            guess = weight_class_for(
                result.sex, result.bodyweight, result.competition.start_date, result.age_group
            )
            if not guess:
                continue
            self.stdout.write(
                f"  {result.competition.start_date}  {result.raw_name:<24} "
                f"{result.bodyweight} кг -> категория {guess}"
            )
            filled += 1
            if not options["dry_run"]:
                result.weight_class = guess
                result.save(update_fields=["weight_class"])
        self.stdout.write(f"попълнени: {filled}")
        if options["dry_run"]:
            self.stdout.write("СУХ ПРОБЕГ, нищо не е записано.")
        elif filled:
            recalculate_records()
            self.stdout.write("рекордите са преизчислени")
