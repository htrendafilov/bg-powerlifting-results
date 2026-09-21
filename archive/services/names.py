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
