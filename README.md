# Daily Stop

A one-page digest of what's trending in AI and tech today. Each source is a
section of cards; click a card to open the repo, story or paper.

**Live:** https://vincent0408.github.io/daily-stop/

## Sources

- **GitHub Trending**: repos gaining the most stars today
- **Hacker News**: top stories on the front page
- **Hugging Face Models**: models trending on the Hub
- **Hugging Face Papers**: today's most upvoted research papers

The page updates automatically a few times a day.

## How it works

GitHub Pages only serves static files, so a scheduled GitHub Actions workflow
runs `build.py`, which fetches every source and writes `static/data/feed.json`.
The workflow then publishes the `static/` folder to Pages. The front end is
plain HTML, CSS and JavaScript with no build step.

The same front end also works with a small FastAPI server for local use, where
each section loads live.

## Run it locally

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000. API docs are at http://localhost:8000/docs.

## Make your own

1. Fork this repo (or copy it into a new public repo).
2. **Settings → Pages → Build and deployment → Source:** choose **GitHub Actions**.
3. **Actions → Refresh feed → Run workflow** to publish the first time.
4. Open `https://<your-username>.github.io/<repo>/`.

Change the update times in `.github/workflows/refresh.yml` (cron times are UTC).
GitHub pauses scheduled workflows after 60 days without repo activity; running
the workflow manually starts them again.

### Optional: the Refresh now button

The button starts the workflow from the page. It asks for a fine-grained
GitHub token limited to your copy of this repo with **Actions: Read and write**
only. The token is kept in your browser's local storage and never leaves it
except to call the GitHub API. Without a token, the button links to the
workflow page instead. Never commit a token to the repo.

## Add a source

1. `cp app/sources/_template.py app/sources/my_source.py`
2. Set `id`, `name`, `homepage` and `color`, then write `fetch()` so it returns
   a list of `Item(title=..., url=..., description=..., metric=..., details=[...])`.
3. Restart the server. A new section, filter chip and colour band appear.

Files starting with `_` are ignored. If one source fails, only its own section
shows an error.

## Configuration

| What | Where |
|---|---|
| GitHub weekly/monthly or one language | `since` / `language` in `app/sources/github_trending.py` |
| AI-only Hacker News | uncomment `keywords` in `app/sources/hackernews.py` |
| Cards per source | `limit` on any source class |
| Section order | `order` on any source class |
| Cache time (local server) | `ttl_seconds` on any source class |
| Show only some sources | `DAILY_STOP_SOURCES=github,hackernews` |

## Project layout

```
build.py               Fetches all sources, writes static/data/feed.json
.github/workflows/     Scheduled workflow that builds and deploys to Pages
app/
  main.py              FastAPI app: /api/sources, /api/feed, /api/feed/{id}
  feed.py              Concurrent fetching, per-source cache, error isolation
  models.py            Item / SourceFeed shapes
  sources/             One module per source, auto-discovered
static/                Front end (HTML/CSS/JS)
```
