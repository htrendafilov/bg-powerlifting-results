from datetime import date
from decimal import Decimal

from django.db import models
from django.utils.text import slugify

from archive.services.names import athlete_name_key, transliterate


class Sex(models.TextChoices):
    M = "M", "Мъже"
    F = "F", "Жени"


class AgeGroup(models.TextChoices):
    SUBJUNIOR = "subjunior", "До 18"
    JUNIOR = "junior", "До 23"
    OPEN = "open", "Открита"
    M1 = "m1", "Ветерани 1 (40–49)"
    M2 = "m2", "Ветерани 2 (50–59)"
    M3 = "m3", "Ветерани 3 (60–69)"
    M4 = "m4", "Ветерани 4 (70+)"


class Equipment(models.TextChoices):
    CLASSIC = "classic", "Класика"
    EQUIPPED = "equipped", "Екип"


class Event(models.TextChoices):
    SBD = "SBD", "Трибой"
    B = "B", "Лег"


class Lift(models.TextChoices):
    SQUAT = "squat", "Клек"
    BENCH = "bench", "Лег"
    DEADLIFT = "deadlift", "Тяга"
    TOTAL = "total", "Тотал"


class MeetLevel(models.TextChoices):
    NATIONAL = "national", "Национално"
    INTERNATIONAL = "international", "Международно"


class FileKind(models.TextChoices):
    EXCEL = "excel", "Ексел"
    PDF = "pdf", "PDF"
    SCAN = "scan", "Снимка на протокол"
    LINK = "link", "Линк"


class RecordOrigin(models.TextChoices):
    STANDARD = "standard", "Норматив"
    SEED = "seed", "Таблица на БФСТ"
    RESULT = "result", "От резултат"


BG_COUNTRIES = {"bg", "bul", "bulgaria", "българия", "бг"}

AGE_RECORD_GROUPS = {
    AgeGroup.SUBJUNIOR: [AgeGroup.SUBJUNIOR, AgeGroup.JUNIOR, AgeGroup.OPEN],
    AgeGroup.JUNIOR: [AgeGroup.JUNIOR, AgeGroup.OPEN],
    AgeGroup.OPEN: [AgeGroup.OPEN],
    AgeGroup.M1: [AgeGroup.M1, AgeGroup.OPEN],
    AgeGroup.M2: [AgeGroup.M2, AgeGroup.OPEN],
    AgeGroup.M3: [AgeGroup.M3, AgeGroup.OPEN],
    AgeGroup.M4: [AgeGroup.M4, AgeGroup.OPEN],
}


def unique_slug(model, value, instance_pk=None):
    base = slugify(value, allow_unicode=False) or "zapis"
    slug = base
    number = 2
    while model.objects.filter(slug=slug).exclude(pk=instance_pk).exists():
        slug = f"{base}-{number}"
        number += 1
    return slug


class Athlete(models.Model):
    name_bg = models.CharField("Име на български", max_length=200, blank=True)
    name_lat = models.CharField("Име на латиница", max_length=200, blank=True)
    sex = models.CharField("Пол", max_length=1, choices=Sex.choices)
    birth_year = models.PositiveSmallIntegerField("Година на раждане", null=True, blank=True)
    adult_confirmed = models.BooleanField(
        "Потвърден над 18",
        default=False,
        help_text="Нужно е само когато годината на раждане липсва, за да се покажат снимки.",
    )
    name_key = models.CharField(max_length=220, blank=True, db_index=True)
    slug = models.SlugField(max_length=220, unique=True)
    notes = models.TextField("Бележка", blank=True)

    class Meta:
        ordering = ["name_bg", "name_lat"]
        verbose_name = "Състезател"
        verbose_name_plural = "Състезатели"

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if self.name_bg and not self.name_lat:
            self.name_lat = transliterate(self.name_bg)
        self.name_key = athlete_name_key(self.name_bg, self.name_lat)
        if not self.slug:
            self.slug = unique_slug(Athlete, self.name_lat or self.name_bg or "sastezatel")
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.name_bg or self.name_lat

    @property
    def allows_public_photos(self):
        if self.birth_year:
            return date.today().year - self.birth_year >= 18
        return self.adult_confirmed


class AthletePhoto(models.Model):
    athlete = models.ForeignKey(Athlete, on_delete=models.CASCADE, related_name="photos")
    year = models.PositiveSmallIntegerField("Година")
    image = models.ImageField("Снимка", upload_to="athletes/%Y/")
    caption = models.CharField("Надпис", max_length=200, blank=True)

    class Meta:
        ordering = ["year", "id"]
        verbose_name = "Снимка"
        verbose_name_plural = "Снимки"

    def __str__(self):
        return f"{self.athlete} ({self.year})"


class Competition(models.Model):
    name = models.CharField("Име", max_length=300)
    slug = models.SlugField(max_length=320, unique=True)
    start_date = models.DateField("Начална дата")
    end_date = models.DateField("Крайна дата", null=True, blank=True)
    city = models.CharField("Град", max_length=120, blank=True)
    country = models.CharField("Държава", max_length=80, default="България")
    level = models.CharField("Ниво", max_length=20, choices=MeetLevel.choices, default=MeetLevel.NATIONAL)
    notes = models.TextField("Бележка", blank=True)

    class Meta:
        ordering = ["-start_date", "name"]
        verbose_name = "Състезание"
        verbose_name_plural = "Състезания"

    def __str__(self):
        return f"{self.name} ({self.start_date.year})"

    def protocol_label(self):
        file_count = getattr(self, "file_count", None)
        has_files = file_count > 0 if file_count is not None else self.files.exists()
        if has_files:
            return ""
        if self.start_date > date.today():
            return "Още не е проведено"
        return "Няма протокол"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Competition, transliterate(f"{self.name}-{self.start_date.year}"))
        super().save(*args, **kwargs)


class CompetitionFile(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="files")
    kind = models.CharField("Вид", max_length=10, choices=FileKind.choices)
    title = models.CharField("Заглавие", max_length=300, blank=True)
    file = models.FileField("Файл", upload_to="protocols/%Y/", blank=True)
    url = models.URLField("Линк", blank=True)
    sort_order = models.PositiveSmallIntegerField("Ред", default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Файл към протокол"
        verbose_name_plural = "Файлове към протокол"

    def __str__(self):
        return self.title or self.file.name or self.url


class Result(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="results")
    athlete = models.ForeignKey(Athlete, on_delete=models.PROTECT, related_name="results")
    raw_name = models.CharField("Име от файла", max_length=200, blank=True)
    country = models.CharField("Държава", max_length=80, blank=True, default="България")
    sex = models.CharField("Пол", max_length=1, choices=Sex.choices)
    age_group = models.CharField("Възраст", max_length=12, choices=AgeGroup.choices)
    equipment = models.CharField("Екипировка", max_length=12, choices=Equipment.choices)
    event = models.CharField("Дисциплина", max_length=3, choices=Event.choices)
    weight_class = models.CharField("Категория", max_length=16)
    bodyweight = models.DecimalField("Тегло", max_digits=5, decimal_places=2, null=True, blank=True)
    place = models.CharField("Място", max_length=8, blank=True)
    club = models.CharField("Клуб", max_length=200, blank=True)
    lot = models.CharField("Жребий", max_length=12, blank=True)
    squat1 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    squat2 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    squat3 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    squat4 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    bench1 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    bench2 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    bench3 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    bench4 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    deadlift1 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    deadlift2 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    deadlift3 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    deadlift4 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    best_squat = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    best_bench = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    best_deadlift = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    total = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    points = models.DecimalField("Точки", max_digits=7, decimal_places=2, null=True, blank=True)
    points_formula = models.CharField("Формула", max_length=20, blank=True)
    review_note = models.CharField("За проверка", max_length=300, blank=True)

    class Meta:
        ordering = ["weight_class", "place", "id"]
        verbose_name = "Резултат"
        verbose_name_plural = "Резултати"
        indexes = [
            models.Index(fields=["competition", "event"]),
            models.Index(fields=["athlete", "competition"]),
        ]

    def __str__(self):
        return f"{self.raw_name or self.athlete} @ {self.competition}"

    @property
    def counts_for_bulgarian_records(self):
        if (self.place or "").strip().upper() == "DD":
            return False
        country = (self.country or "").strip().lower()
        return country in BG_COUNTRIES

    def successful(self, value):
        if value is None:
            return None
        if value <= 0:
            return None
        return value

    def lift_value(self, lift):
        if lift == Lift.SQUAT:
            return self._best_or_fourth("best_squat", "squat4")
        if lift == Lift.BENCH:
            return self._best_or_fourth("best_bench", "bench4")
        if lift == Lift.DEADLIFT:
            return self._best_or_fourth("best_deadlift", "deadlift4")
        if lift == Lift.TOTAL and self.event == Event.SBD:
            return self.successful(self.total)
        return None

    def _best_or_fourth(self, best_name, fourth_name):
        best = self.successful(getattr(self, best_name))
        fourth = self.successful(getattr(self, fourth_name))
        if best is None:
            return fourth
        if fourth is None:
            return best
        return max(best, fourth)


class Record(models.Model):
    sex = models.CharField(max_length=1, choices=Sex.choices)
    age_group = models.CharField(max_length=12, choices=AgeGroup.choices)
    equipment = models.CharField(max_length=12, choices=Equipment.choices)
    event = models.CharField(max_length=3, choices=Event.choices)
    lift = models.CharField(max_length=12, choices=Lift.choices)
    weight_class = models.CharField(max_length=16)
    value_kg = models.DecimalField(max_digits=7, decimal_places=2)
    athlete = models.ForeignKey(Athlete, null=True, blank=True, on_delete=models.PROTECT, related_name="records")
    result = models.ForeignKey(Result, null=True, blank=True, on_delete=models.SET_NULL, related_name="records_set_by")
    origin = models.CharField(max_length=12, choices=RecordOrigin.choices)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["sex", "age_group", "equipment", "event", "lift", "weight_class", "valid_from"]
        verbose_name = "Рекорд"
        verbose_name_plural = "Рекорди"
        indexes = [
            models.Index(fields=["sex", "age_group", "equipment", "event", "lift", "weight_class", "valid_to"]),
        ]

    def __str__(self):
        holder = self.athlete.display_name if self.athlete_id else self.get_origin_display()
        return f"{self.get_lift_display()} {self.weight_class} {self.value_kg} {holder}"

    @property
    def is_current(self):
        return self.valid_to is None and self.origin != RecordOrigin.STANDARD


def kg(value):
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
