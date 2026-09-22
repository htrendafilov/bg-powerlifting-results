import re

# Закон за транслитерацията, поток от 2009 г.
_LETTERS = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sht",
    "ъ": "a",
    "ь": "y",
    "ю": "yu",
    "я": "ya",
}


def is_cyrillic(text):
    return any("а" <= char.lower() <= "я" or char.lower() in "ьъ" for char in text)


def transliterate(text):
    pieces = []
    for char in text:
        lower = char.lower()
        mapped = _LETTERS.get(lower)
        if mapped is None:
            pieces.append(char)
            continue
        if char.isupper():
            mapped = mapped.capitalize()
        pieces.append(mapped)
    return "".join(pieces)


def name_tokens(text):
    if not text:
        return []
    cleaned = transliterate(text).lower().replace("ё", "е")
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return [token for token in cleaned.split() if token]


def athlete_name_key(name_bg, name_lat):
    tokens = name_tokens(name_lat) or name_tokens(name_bg)
    return " ".join(sorted(tokens))


# Spellings the sources actually use that are not the 2009 standard.
_FOLD = [
    ("shtch", "sht"), ("tch", "ch"), ("kh", "h"), ("tz", "ts"), ("cz", "ts"),
    ("ph", "f"), ("ck", "k"), ("qu", "kv"), ("x", "ks"), ("w", "v"), ("tc", "ch"),
]

# Endings the Russian and older Latin spellings use for Bulgarian names.
_ENDINGS = [
    (r"iy$", "i"),      # Evgeniy -> Евгени, Rachkovskiy -> Рачковски
    (r"ia$", "iya"),    # Ilia -> Илия
    (r"^io", "yo"),     # Iordan -> Йордан
    (r"^ia", "ya"),     # Ianko -> Янко
    # Bulgarian "й" only ever follows a vowel, so a trailing y after a
    # consonant is someone writing "и": Georgy -> Георги.
    (r"([bcdfghjklmnpqrstvwxz])y$", r"\1i"),
]
_PAIRS = [
    ("sht", "щ"), ("zh", "ж"), ("ch", "ч"), ("sh", "ш"), ("ts", "ц"),
    ("yu", "ю"), ("ya", "я"),
    ("a", "а"), ("b", "б"), ("v", "в"), ("g", "г"), ("d", "д"), ("e", "е"),
    ("z", "з"), ("i", "и"), ("y", "й"), ("k", "к"), ("l", "л"), ("m", "м"),
    ("n", "н"), ("o", "о"), ("p", "п"), ("r", "р"), ("s", "с"), ("t", "т"),
    ("u", "у"), ("f", "ф"), ("h", "х"), ("c", "к"), ("j", "ж"), ("q", "к"),
]
# ъ and ь both come back as "a"/"y", so the words that carry them are listed.
_WORDS = {
    "petar": "Петър", "dimitar": "Димитър", "aleksandar": "Александър",
    "aleksander": "Александър", "alexander": "Александър", "alexandar": "Александър",
    "alexandr": "Александър", "aleksandr": "Александър",
    "todor": "Тодор", "bozhidar": "Божидар", "kiril": "Кирил",
    "angel": "Ангел", "georgi": "Георги", "ivaylo": "Ивайло", "ivailo": "Ивайло",
    "hristo": "Христо", "christo": "Христо", "hristov": "Христов", "christov": "Христов",
    "mihail": "Михаил", "michail": "Михаил", "mihailov": "Михайлов", "michailov": "Михайлов",
    "mihaylov": "Михайлов", "kolyo": "Кольо", "koljo": "Кольо",
    "lachezar": "Лъчезар", "lachezarov": "Лъчезаров", "tsvetan": "Цветан",
    "vaptsarov": "Вапцаров", "asparuh": "Аспарух", "krastev": "Кръстев",
    "krastyo": "Кръстьо", "panteley": "Пантелей", "zdravko": "Здравко",
    "andrey": "Андрей", "sergey": "Сергей", "nikolay": "Николай", "atanas": "Атанас",
    "stanislav": "Станислав", "svetoslav": "Светослав", "vladislav": "Владислав",
    "parvan": "Първан", "parvanov": "Първанов", "parvanova": "Първанова",
    "garlov": "Гърлов", "garlova": "Гърлова", "varbanov": "Върбанов",
    "varbanova": "Върбанова", "valchanov": "Вълчанов", "valchanova": "Вълчанова",
    "valkanov": "Вълканов", "valkanova": "Вълканова", "silvestar": "Силвестър",
    "sadak": "Садък", "belkaz": "Белкъз", "vaklinov": "Ваклинов", "garkov": "Гърков", "tarnev": "Търнев",
}


def fold_latin(text):
    """Normalise a non-standard spelling towards the 2009 transliteration."""
    lowered = text.lower()
    for bad, good in _FOLD:
        lowered = lowered.replace(bad, good)
    for pattern, replacement in _ENDINGS:
        lowered = re.sub(pattern, replacement, lowered)
    return lowered


def reverse_transliterate(text):
    return " ".join(_word(part) for part in text.split())


def _word(word):
    cleaned = re.sub(r"#\d+$", "", word).strip()
    if not cleaned:
        return ""
    known = _WORDS.get(cleaned.lower())
    if known:
        return known
    lowered = fold_latin(cleaned)
    out = []
    index = 0
    while index < len(lowered):
        for latin, cyr in _PAIRS:
            if lowered.startswith(latin, index):
                out.append(cyr)
                index += len(latin)
                break
        else:
            out.append(lowered[index])
            index += 1
    result = "".join(out)
    return "-".join(part[:1].upper() + part[1:] for part in result.split("-"))
