from datetime import date

from app.db import db_session, init_db, set_setting
from app.menu import (
    attach_dates,
    current_week_start,
    generate_menu,
    get_or_create_week_menu,
    pick_recipe_ids,
    search_recipes,
    set_day_recipe,
    today_menu_item,
    week_length,
)
from tests.conftest import insert_recipe


def test_current_week_start_is_monday():
    assert current_week_start(date(2026, 9, 9)) == date(2026, 9, 7)
    assert current_week_start(date(2026, 9, 7)) == date(2026, 9, 7)


def test_pick_recipe_ids_unique_when_enough():
    ids = pick_recipe_ids([1, 2, 3, 4, 5], 5)
    assert len(ids) == 5
    assert set(ids) == {1, 2, 3, 4, 5}


def test_pick_recipe_ids_repeats_when_needed():
    ids = pick_recipe_ids([1, 2], 5)
    assert len(ids) == 5
    assert set(ids) <= {1, 2}
    assert ids.count(1) + ids.count(2) == 5


def test_pick_recipe_ids_empty():
    assert pick_recipe_ids([], 5) == []


def test_generate_menu_distinct(db_path):
    init_db()
    with db_session() as conn:
        for i in range(5):
            insert_recipe(conn, name=f"Recept {i}")
        menu = generate_menu(conn, date(2026, 9, 7))
        names = [d["recipe"].name for d in menu["days"]]
        assert menu["week_length"] == 5
        assert len(names) == 5
        assert len(set(names)) == 5


def test_week_length_change_does_not_autogenerate(db_path):
    init_db()
    with db_session() as conn:
        for i in range(5):
            insert_recipe(conn, name=f"Recept {i}")
        first = generate_menu(conn, date(2026, 9, 7))
        first_ids = [d["recipe"].id for d in first["days"]]
        set_setting(conn, "week_length", "7")
        assert week_length(conn) == 7
        current = get_or_create_week_menu(conn, date(2026, 9, 7))
        current_ids = [d["recipe"].id for d in current["days"] if d["recipe"]]
        assert current_ids == first_ids
        padded = attach_dates(current)
        assert len(padded["days"]) == 7
        assert padded["days"][5]["recipe"] is None
        assert padded["days"][6]["recipe"] is None


def test_search_and_set_day_recipe(db_path):
    init_db()
    with db_session() as conn:
        gulyas = insert_recipe(conn, name="Gulyás")
        insert_recipe(conn, name="Lencsefőzelék")
        insert_recipe(conn, name="Tökfőzelék")
        names = [r.name for r in search_recipes(conn, "főzelék")]
        assert names == ["Lencsefőzelék", "Tökfőzelék"]
        assert [r.name for r in search_recipes(conn, "GULY")] == ["Gulyás"]
        generate_menu(conn, date(2026, 9, 7))
        menu = set_day_recipe(conn, 1, gulyas, date(2026, 9, 7))
        assert menu["days"][1]["recipe"].id == gulyas


def test_today_weekend_with_five_day_week(db_path):
    init_db()
    with db_session() as conn:
        insert_recipe(conn)
        generate_menu(conn, date(2026, 9, 7))
        assert today_menu_item(conn, date(2026, 9, 12)) is None
        monday = today_menu_item(conn, date(2026, 9, 7))
        assert monday is not None
        assert monday["recipe"] is not None
