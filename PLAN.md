# Lunchie — Implementation Plan

Greenfield local app: store recipes, randomly generate a weekly lunch menu, two UIs plus REST for Home Assistant.

## Goals

- CRUD for recipes (ingredients, method, nutrition, cook time, servings)
- Random weekly menu, **5 or 7 days** (setting)
- **Admin UI**: recipes, settings, UI language
- **User UI**: current week, regenerate, recipe detail
- **Docker** on the LAN, port **7077**
- **HA**: iframe of the user UI + REST for sensors
- **No auth** (home LAN only)
- **Pluggable UI language**: default **English**; **Hungarian** file shipped; switch in admin

**Servings:** `serves` is a label (e.g. 4). Ingredients and nutrition are **per 1 person**. No scaling in v1.

**Language:** UI chrome is translated. Recipe names, ingredients, and instructions are **not** translated — stored and shown as typed (Hungarian).

## Stack

| Layer | Choice |
|---|---|
| API / pages | Python 3.12, FastAPI, Jinja2, htmx |
| DB | SQLite (`/data/lunchie.db`) |
| i18n | JSON catalogs + Jinja `t()` helper |
| CSS | Pico CSS |
| Container | `docker-compose`, port **7077** |
| HA | iframe + REST sensors |

Single process. Named volume for the DB.

## Layout

```
lunchie/
  PLAN.md
  README.md
  Dockerfile
  docker-compose.yml
  requirements.txt
  app/
    main.py
    db.py
    models.py
    menu.py
    i18n.py
    locales/
      en.json
      hu.json
    routers/
      pages.py
      api.py
    templates/
      base.html
      user/week.html
      user/recipe_detail.html
      admin/recipes.html
      admin/recipe_form.html
      admin/settings.html
    static/
      style.css
      htmx.min.js
```

Adding a language later = new `locales/{code}.json` + entry in the admin dropdown.

## Data model

**recipes**
- `id`, `name` (unique), `instructions`
- `serves` (int, ≥ 1, default 1)
- `prep_time_minutes`
- `calories_kcal`, `protein_g`, `carbohydrates_g`, `fats_g`, `salt_g` — per person
- `created_at`, `updated_at`

**ingredients**
- `id`, `recipe_id` (FK, cascade)
- `name`, `amount`, `unit` (`g` | `kg` | `ml` | `l` | `pcs` | `tsp` | `tbsp`) — per person

**settings** (key/value)
- `week_length`: `"5"` or `"7"` (default `5`)
- `week_starts_on`: `"monday"` (v1 fixed)
- `ui_language`: `"en"` (default) or `"hu"`

**weekly_menus** / **menu_items**
- `week_start` (Monday date, unique)
- `day_index` 0 = Monday

**Generation:** distinct recipes if enough exist; repeats only after the pool is exhausted. Regen replaces the current week. Zero recipes → empty state linking to admin.

## i18n

- Nested JSON, dotted keys (`nav.menu`, `week.regenerate`, `recipe.serves`)
- Missing key → fall back to **en**, then the key itself
- `html lang="{{ lang }}"` on `base.html`
- Admin Settings: language select (English / Magyar); saving reloads UI
- Units stay as symbols; day names and labels come from catalogs
- JSON API is language-agnostic (recipe fields as stored)

## UIs (htmx, no login)

**User (`/`)**
- Header: week of {date}
- Day cards: name, kcal/person, minutes, Serves N
- Click → method, per-person ingredients, per-person nutrition, time, serves
- **Regenerate week** (confirm)
- Today highlighted
- All chrome via `t()`

**Admin (`/admin`)**
- Recipe table: name, time, kcal, serves, edit/delete
- Add/edit form: name, serves (≥ 1), time, 5 nutrition fields, instructions
- Ingredients: htmx add/remove rows (name, amount, unit)
- Settings: 5 vs 7 days (no auto-regen) + UI language

## HTTP

**Pages:** `/`, recipe detail, `POST /menu/regenerate`, admin CRUD, settings.

**JSON**
- `GET /api/health`
- `GET /api/menu/today` — includes `serves` + per-person nutrition/ingredients
- `GET /api/menu/current`
- `GET /api/recipes`, `GET /api/recipes/{id}`
- `POST /api/menu/regenerate`

Bind **`0.0.0.0:7077`**.

## Docker

```yaml
services:
  lunchie:
    build: .
    ports: ["7077:7077"]
    volumes: ["lunchie-data:/data"]
    restart: unless-stopped
volumes:
  lunchie-data:
```

- `uvicorn app.main:app --host 0.0.0.0 --port 7077`
- `DATABASE_PATH=/data/lunchie.db`
- Schema created on startup if missing

## Home Assistant

Iframe: `http://<host>:7077/`

REST sensor from `/api/menu/today` (`name`, `serves`, `prep_time_minutes`, nutrition). Optional `rest_command` for regenerate. HA must use LAN/host IP, not `localhost` from HA OS.

## v1 out of scope

Auth, shopping list, scaling to N people, leftover rules, import/export, photos, HTTPS, translating recipe content, extra locales beyond en/hu.

## Implementation order

1. Skeleton + SQLite + Docker + health on **7077**
2. i18n helper + `en.json` / `hu.json` + `t()` in templates
3. Recipe CRUD (`serves`, ingredients)
4. Settings (week length + language)
5. Generator + user week + detail + regenerate
6. JSON APIs
7. README (Docker + HA yaml, port **7077**)
8. Seed 3–5 Hungarian recipes

## Done when

- `docker compose up --build` serves both UIs on **`:7077`**
- Recipes persist on volume
- 5/7-day random menu works
- User sees method, per-person metric ingredients/nutrition, time, serves N
- UI defaults to English and switches to Hungarian from admin
- `/api/menu/today` is enough for an HA sensor
- README has copy-paste HA yaml
