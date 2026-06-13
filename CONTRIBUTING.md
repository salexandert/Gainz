# Contributing To Gainz

## Public Docs Source Of Truth

Use `docs/` as the source of truth for public product documentation.

When a product improvement changes the user flow, update the relevant Markdown page in `docs/` first:

- `docs/user-walkthrough.md` for the end-to-end app flow.
- `docs/download.md` for packaged releases, launcher behavior, or install notes.
- `docs/how-gainz-calculates-basis.md` for basis methodology changes.
- `docs/guides/*.md` for focused import, reconciliation, audit packet, CPA, and troubleshooting guides.
- `docs/assets/screenshots/` for synthetic screenshots that are safe to publish.

The website is built from `docs/`. Netlify can deploy the site from this repo using `netlify.toml`; `.github/workflows/pages.yml` validates that the docs site builds. The GitHub Wiki pages are generated from `docs/` by `scripts/generate_wiki_home.py` and synced by `.github/workflows/sync-wiki.yml`.

Do not hand-maintain a second long-form copy of the same walkthrough in the wiki or website. The generated wiki includes inline screenshots, a walkthrough, guide index, and docs publishing flow. Wiki edits for product docs should happen in `docs/` first because the next sync replaces stale wiki-only pages.

## Local Checks

Before pushing public docs or release changes, run:

```powershell
python .\scripts\generate_wiki_home.py --output-dir .\build\wiki
python -m pytest Tests
git diff --check
```

Never commit private saves, exports, source tax files, audit packets, logs, uploaded CSVs, local plans, or instance data.
