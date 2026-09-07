# Lunchie

Weekly lunch menu generator. Add recipes, randomly generate a Mon–Fri or full-week menu, view details and nutrition. Built for local Docker + Home Assistant.

## Features

- Recipe CRUD (ingredients, instructions, nutrition, prep time, servings)
- Random weekly menu (5 or 7 days)
- User UI: week view, regenerate, recipe detail
- Admin UI: recipes + settings (week length, UI language)
- English UI by default, Hungarian translation included
- REST API for Home Assistant sensors
- No authentication (home LAN only)

Nutrition and ingredients are **per person**. `Serves N` is a label only.

## Quick start

```bash
docker compose up --build -d
```

Open http://localhost:7077/

- **Menu:** `/`
- **Admin:** `/admin/recipes`
- **Settings:** `/admin/settings`
- **Health:** `/api/health`

Data is stored in the `lunchie-data` Docker volume (`/data/lunchie.db`).

### Local dev (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data
DATABASE_PATH=./data/lunchie.db uvicorn app.main:app --host 0.0.0.0 --port 7077 --reload
```

### Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Releases

Push a `v*.*.*` tag, or run **Actions → Release → Run workflow** with a version like `1.0.0`. That creates a GitHub Release and publishes:

```text
ghcr.io/<owner>/lunchie:v1.0.0
ghcr.io/<owner>/lunchie:1.0.0
ghcr.io/<owner>/lunchie:latest
```

The package must be public (or you must be logged in) to pull:

```bash
docker pull ghcr.io/<owner>/lunchie:latest
```

Replace `image: .` / `build: .` in `docker-compose.yml` with that image if you want to run a released build. The package visibility is under **Repo → Packages**. First publish may stay private until you change it.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | `{ "ok": true }` |
| GET | `/api/menu/today` | Today's lunch (or null recipe) |
| GET | `/api/menu/current` | Full current week |
| POST | `/api/menu/regenerate` | New random week |
| GET | `/api/recipes` | All recipes |
| GET | `/api/recipes/{id}` | One recipe |

## Home Assistant

Replace `<host>` with your machine’s LAN IP (not `localhost` if HA runs elsewhere).

### Iframe card

```yaml
type: iframe
url: http://<host>:7077/
aspect_ratio: 100%
```

### REST sensor (today’s lunch)

```yaml
rest:
  - resource: http://<host>:7077/api/menu/today
    scan_interval: 300
    sensor:
      - name: Lunchie today
        value_template: "{{ value_json.recipe.name if value_json.recipe else 'None' }}"
        json_attributes_path: "$.recipe"
        json_attributes:
          - serves
          - prep_time_minutes
          - calories_kcal
          - protein_g
          - carbohydrates_g
          - fats_g
          - salt_g
```

### Regenerate button (optional)

```yaml
rest_command:
  lunchie_regenerate:
    url: http://<host>:7077/api/menu/regenerate
    method: POST
```

## Language

UI strings live in `app/locales/en.json` and `app/locales/hu.json`. Change language under **Admin → Settings**. Recipe content is not translated (enter Hungarian text as-is).

To add a language: create `app/locales/{code}.json`, add the code to `SUPPORTED_LANGUAGES` in `app/i18n.py`, and expose it in the settings template.

## License

Personal / home use.
