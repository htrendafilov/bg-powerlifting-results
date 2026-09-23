"""Attach the OpenPowerlifting page of each meet imported from it.

The rows came from the bulk export, which carries no link back, so the address
is looked up once per federation in that federation's meet list.
"""

import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

from django.core.management.base import BaseCommand

from archive.models import Competition, CompetitionFile, FileKind, MeetLevel

SITE = "https://www.openpowerlifting.org"
AGENT = "powerliftingbg.fyi archive (+https://powerliftingbg.fyi)"
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
PATH = re.compile(r'href="(/m/[^"]+)"')
TAGS = re.compile(r"<[^>]+>")


class Command(BaseCommand):
    help = "Слага линк към OpenPowerlifting на турнирите, внесени оттам."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--delay", type=float, default=1.0)

    def handle(self, *args, **options):
        pending = defaultdict(list)
        for meet in Competition.objects.filter(level=MeetLevel.INTERNATIONAL):
            if meet.files.filter(kind=FileKind.OPL).exists():
                continue
            found = re.search(r"Федерация:\s*([\w-]+)", meet.notes or "")
            if found:
                pending[found.group(1).lower()].append(meet)

        total = sum(len(v) for v in pending.values())
        self.stdout.write(f"турнири без линк: {total}, федерации: {len(pending)}")
        linked = missed = 0
        for fed, meets in sorted(pending.items()):
            listing = self._fetch(f"{SITE}/mlist/{fed}")
            time.sleep(options["delay"])
            if listing is None:
                self.stdout.write(f"  {fed}: списъкът не се чете, {len(meets)} пропуснати")
                missed += len(meets)
                continue
            index = self._index(listing)
            hit = 0
            for meet in meets:
                path = self._match(index, meet)
                if not path:
                    missed += 1
                    continue
                hit += 1
                linked += 1
                if not options["dry_run"]:
                    CompetitionFile.objects.create(
                        competition=meet,
                        kind=FileKind.OPL,
                        title=meet.name,
                        url=f"{SITE}{path}",
                        sort_order=9,
                    )
            self.stdout.write(f"  {fed:<14} {hit}/{len(meets)} намерени")
        self.stdout.write(f"\nсложени линкове: {linked}   без съответствие: {missed}")
        if options["dry_run"]:
            self.stdout.write("СУХ ПРОБЕГ, нищо не е записано.")

    def _fetch(self, url):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError):
            return None

    def _index(self, html):
        """(date, tidied name) -> path, plus a date-only fallback."""
        by_both, by_date = {}, defaultdict(list)
        for row in ROW.findall(html):
            path = PATH.search(row)
            cells = [TAGS.sub("", c).strip() for c in CELL.findall(row)]
            if not path or len(cells) < 4:
                continue
            day, name = cells[1], cells[3]
            by_both[(day, self._tidy(name))] = path.group(1)
            by_date[day].append(path.group(1))
        return by_both, by_date

    def _match(self, index, meet):
        by_both, by_date = index
        day = meet.start_date.isoformat()
        found = by_both.get((day, self._tidy(meet.name)))
        if found:
            return found
        # A meet the federation renamed still sits alone on its date.
        same_day = by_date.get(day) or []
        return same_day[0] if len(same_day) == 1 else None

    @staticmethod
    def _tidy(name):
        return re.sub(r"[^a-z0-9]+", "", (name or "").lower())
