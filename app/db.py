import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

_DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "lunchie.db")


def get_database_path() -> str:
    return os.environ.get("DATABASE_PATH", _DEFAULT_DB_PATH)

UNITS = ("g", "kg", "ml", "l", "pcs", "tsp", "tbsp")

SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    instructions TEXT NOT NULL DEFAULT '',
    serves INTEGER NOT NULL DEFAULT 1 CHECK (serves >= 1),
    prep_time_minutes INTEGER NOT NULL DEFAULT 0 CHECK (prep_time_minutes >= 0),
    calories_kcal REAL NOT NULL DEFAULT 0,
    protein_g REAL NOT NULL DEFAULT 0,
    carbohydrates_g REAL NOT NULL DEFAULT 0,
    fats_g REAL NOT NULL DEFAULT 0,
    salt_g REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    unit TEXT NOT NULL DEFAULT 'g'
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS weekly_menus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT NOT NULL UNIQUE,
    generated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    weekly_menu_id INTEGER NOT NULL REFERENCES weekly_menus(id) ON DELETE CASCADE,
    day_index INTEGER NOT NULL,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    UNIQUE (weekly_menu_id, day_index)
);

CREATE INDEX IF NOT EXISTS idx_ingredients_recipe ON ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_menu ON menu_items(weekly_menu_id);
"""

DEFAULT_SETTINGS = {
    "week_length": "5",
    "week_starts_on": "monday",
    "ui_language": "en",
}


def _ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    path = get_database_path()
    _ensure_parent(path)
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db_session() as conn:
        conn.executescript(SCHEMA)
        conn.execute("PRAGMA foreign_keys = ON")
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default if default is not None else DEFAULT_SETTINGS.get(key)
    return row["value"]


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
