import json

from app.i18n import LOCALES_DIR, t, get_language, load_catalogs, make_translator


def _flatten(data: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in data.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(_flatten(value, full))
        else:
            keys.add(full)
    return keys


def test_get_language_falls_back():
    assert get_language("hu") == "hu"
    assert get_language("en") == "en"
    assert get_language("de") == "en"
    assert get_language(None) == "en"


def test_english_and_hungarian_keys_match():
    en = json.loads((LOCALES_DIR / "en.json").read_text(encoding="utf-8"))
    hu = json.loads((LOCALES_DIR / "hu.json").read_text(encoding="utf-8"))
    assert _flatten(en) == _flatten(hu)


def test_translation_and_fallback():
    load_catalogs()
    assert t("nav.menu", "en") == "Menu"
    assert t("nav.menu", "hu") == "Menü"
    assert t("missing.key", "hu") == "missing.key"
    assert t("week.of", "en", date="2026-09-07") == "Week of 2026-09-07"
    assert t("week.of", "en") == "Week of {date}"


def test_make_translator():
    load_catalogs()
    hu = make_translator("hu")
    assert hu("recipe.serves_n", n=4) == "4 főre"
