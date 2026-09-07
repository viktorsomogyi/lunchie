import json
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
SUPPORTED_LANGUAGES = ("en", "hu")
DEFAULT_LANGUAGE = "en"

_catalogs: dict[str, dict] = {}


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    items: dict[str, str] = {}
    for key, value in data.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            items.update(_flatten(value, full))
        else:
            items[full] = str(value)
    return items


def load_catalogs() -> None:
    global _catalogs
    _catalogs = {}
    for code in SUPPORTED_LANGUAGES:
        path = LOCALES_DIR / f"{code}.json"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                _catalogs[code] = _flatten(json.load(f))
        else:
            _catalogs[code] = {}


def get_language(code: str | None) -> str:
    if code in SUPPORTED_LANGUAGES:
        return code  # type: ignore[return-value]
    return DEFAULT_LANGUAGE


def t(key: str, lang: str | None = None, **kwargs) -> str:
    if not _catalogs:
        load_catalogs()
    language = get_language(lang)
    catalogs = _catalogs or {}
    text = catalogs.get(language, {}).get(key)
    if text is None:
        text = catalogs.get(DEFAULT_LANGUAGE, {}).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def make_translator(lang: str):
    language = get_language(lang)

    def translate(key: str, **kwargs) -> str:
        return t(key, language, **kwargs)

    return translate
