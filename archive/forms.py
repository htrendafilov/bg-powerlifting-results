from django import forms

from archive.models import AgeGroup, Competition, Equipment, Event, MeetLevel, Sex


class ImportForm(forms.Form):
    competition = forms.ModelChoiceField(
        label="Съществуващ турнир",
        queryset=Competition.objects.all(),
        required=False,
    )
    name = forms.CharField(label="Име на нов турнир", required=False)
    start_date = forms.DateField(
        label="Дата",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    city = forms.CharField(label="Град", required=False)
    level = forms.ChoiceField(label="Ниво", choices=MeetLevel.choices, initial=MeetLevel.NATIONAL)
    upload = forms.FileField(label="Файл (.xlsx или .csv)")
    default_sex = forms.ChoiceField(
        label="Пол, ако го няма във файла",
        choices=[("", "От файла")] + list(Sex.choices),
        required=False,
    )
    default_equipment = forms.ChoiceField(
        label="Екипировка",
        choices=[("auto", "От файла")] + list(Equipment.choices),
        initial="auto",
    )
    default_event = forms.ChoiceField(
        label="Дисциплина",
        choices=[("auto", "От файла")] + list(Event.choices),
        initial="auto",
    )
    replace = forms.BooleanField(
        label="Замени вече въведените редове на този турнир",
        required=False,
        initial=True,
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("competition") and not cleaned.get("name"):
            raise forms.ValidationError("Избери турнир или напиши име на нов.")
        return cleaned


class RecordFilterForm(forms.Form):
    sex = forms.ChoiceField(label="Пол", choices=Sex.choices, initial=Sex.M)
    age_group = forms.ChoiceField(label="Възраст", choices=AgeGroup.choices, initial=AgeGroup.OPEN)
    equipment = forms.ChoiceField(label="Екипировка", choices=Equipment.choices, initial=Equipment.CLASSIC)
    event = forms.ChoiceField(label="Дисциплина", choices=Event.choices, initial=Event.SBD)
