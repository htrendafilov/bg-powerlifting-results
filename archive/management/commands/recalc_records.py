from django.core.management.base import BaseCommand

from archive.services.records import recalculate_records


class Command(BaseCommand):
    help = "Пресмята рекордите от всички въведени резултати."

    def handle(self, *args, **options):
        recalculate_records()
        self.stdout.write("Рекордите са пресметнати.")
