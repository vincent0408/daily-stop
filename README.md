# Daily Stop

A personal morning page for AI / LLM / tech news. Each source becomes a
section of cards; clicking a card opens the repo, story or paper.

Sources included: GitHub Trending, Hacker News, Hugging Face trending
models, Hugging Face daily papers.

## Run it

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000

## Deploy free on GitHub Pages

A GitHub Actions workflow runs `build.py` on a schedule, writes
`data/feed.json`, and publishes the `static/` folder to Pages. No server needed.

**Quickest:** install the [GitHub CLI](https://cli.github.com), then run `./deploy.sh`
from this folder. It signs you in, creates a public `daily-stop` repo, pushes,
enables Pages and publishes the first feed. Prefer to do it by hand:

1. Create a **public** repo on GitHub (e.g. `daily-stop`) and push this folder to its `main` branch.
2. In the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. **Actions** tab → **Refresh feed** → **Run workflow** to publish the first time.
4. Open `https://<your-username>.github.io/<repo>/`.

The schedule lives in `.github/workflows/refresh.yml` (UTC cron times; the
defaults are 06:30, 12:00 and 18:00 Taiwan time). Pushing to `main` also redeploys.
GitHub may start scheduled runs a few minutes late and pauses them after 60 days
without repo activity. Running the workflow manually starts them again.

### The Refresh now button

On the Pages site, **Refresh now** starts the workflow and reloads the page when
the new feed is live (usually 1–2 minutes). The first time, it asks for a GitHub token:

1. GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate new token.
2. Repository access: **Only select repositories** → this repo.
3. Permissions: **Actions → Read and write**. Nothing else.
4. Set an expiry and paste the token into the dialog.

The token is stored only in that browser's local storage and is never part of the
site's code. Use the key button next to Refresh to replace or remove it. Without a
token, the dialog links to the workflow page where you can press **Run workflow**.

Never commit a token to the repo. Anyone can read a public Pages site's files.

## Project layout

```
build.py               Fetches all sources and writes static/data/feed.json (for Pages)
.github/workflows/
  refresh.yml          Scheduled + manual workflow that builds and deploys to Pages
app/
  main.py              FastAPI app: /api/sources, /api/feed, /api/feed/{id}
  feed.py              Parallel fetching + per-source cache, error isolation
  models.py            Item / SourceFeed shapes shared by every source
  sources/
    __init__.py        Registry: auto-imports every module in this folder
    base.py            Source base class
    github_trending.py
    hackernews.py
    huggingface.py     Two sources: trending models + daily papers
    _template.py       Copy this to add a source
static/                Front end (plain HTML/CSS/JS, no build step). Works with the
                       local server or with data/feed.json on Pages.
```

## Add a new source

1. `cp app/sources/_template.py app/sources/lobsters.py`
2. Set `id`, `name`, `homepage`, `color`, then write `fetch()` so it returns
   a list of `Item(title=..., url=..., description=..., metric=..., details=[...])`.
3. Restart the server. A new section, filter chip and colour band appear.

Files whose names start with `_` are ignored, so the template never loads.
If a source raises an error, only its own section shows the problem.

## Tune it

| What | Where |
|---|---|
| GitHub weekly/monthly or one language | `since` / `language` in `github_trending.py` |
| AI-only Hacker News | uncomment `keywords` in `hackernews.py` |
| Cards per source | `limit` on any source class |
| Cache time | `ttl_seconds` on any source class (default 30 min) |
| Section order | `order` on any source class |
| Show only some sources | `DAILY_STOP_SOURCES=github,hackernews uvicorn app.main:app` |

"Refresh all" bypasses the cache. Loading the page normally uses cached
results, so reopening it during the day is instant.

## API

- `GET /api/sources` – enabled sources and their colours
- `GET /api/feed?refresh=true` – every source at once
- `GET /api/feed/{id}?refresh=true` – one source

Interactive docs: http://localhost:8000/docs
