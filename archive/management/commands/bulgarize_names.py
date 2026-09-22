"""Fill in Cyrillic names for lifters that only reached us in Latin.

International protocols carry no Cyrillic, so an athlete known only from them
shows up as "Ivaylo Hristov" on a Bulgarian site. Names already read from a
Bulgarian protocol are the dictionary; whatever is not in it is converted by
rule and flagged, because the sources spell names in several ways and a rule
cannot always tell "Марков" from "Мърков".
"""

import re
from collections import Counter

from django.core.management.base import BaseCommand

from archive.models import Athlete
from archive.services.names import fold_latin, reverse_transliterate, transliterate


class Command(BaseCommand):
    help = "Попълва имената на кирилица за състезателите, които са само на латиница."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--redo", action="store_true", help="преизчислява и вече изведените")

    def handle(self, *args, **options):
        vocab = self._vocabulary()
        self.stdout.write(f"думи, научени от български протоколи: {len(vocab)}")

        targets = Athlete.objects.exclude(name_lat="")
        targets = targets.filter(name_bg="") if not options["redo"] else targets.filter(
            name_bg_auto=True
        ) | targets.filter(name_bg="")

        from_vocab = by_rule = 0
        samples = []
        for athlete in targets.distinct():
            parts, used_vocab = [], False
            for token in athlete.name_lat.split():
                word, marker = self._split_marker(token)
                known = vocab.get(fold_latin(word))
                if known:
                    parts.append(known + marker)
                    used_vocab = True
                else:
                    parts.append(reverse_transliterate(word) + marker)
            name = " ".join(parts)
            from_vocab += int(used_vocab)
            by_rule += int(not used_vocab)
            if len(samples) < 12:
                samples.append(f"{athlete.name_lat}  ->  {name}")
            if not options["dry_run"]:
                athlete.name_bg = name
                athlete.name_bg_auto = True
                athlete.save()

        self.stdout.write(f"с помощ от речника: {from_vocab}   само по правила: {by_rule}")
        for line in samples:
            self.stdout.write(f"   {line}")
        if options["dry_run"]:
            self.stdout.write("СУХ ПРОБЕГ, нищо не е записано.")

    def _vocabulary(self):
        counts = {}
        for athlete in Athlete.objects.exclude(name_bg="").filter(name_bg_auto=False):
            for token in athlete.name_bg.split():
                counts.setdefault(transliterate(token).lower(), Counter())[token] += 1
        return {key: word.most_common(1)[0][0] for key, word in counts.items()}

    def _split_marker(self, token):
        """OpenPowerlifting appends #1/#2 to tell two same-named lifters apart."""
        match = re.match(r"^(.*?)(#\d+)$", token)
        return (match.group(1), match.group(2)) if match else (token, "")
