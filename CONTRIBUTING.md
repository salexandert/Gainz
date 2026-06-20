# Contributing To Gainz

## Public Docs Source Of Truth

Use `docs/` as the source of truth for public product documentation.

When a product improvement changes the user flow, update the relevant Markdown page in `docs/` first:

- `docs/user-walkthrough.md` for the end-to-end app flow.
- `docs/download.md` for packaged releases, launcher behavior, or install notes.
- `docs/how-gainz-calculates-basis.md` for basis methodology changes.
- `docs/guides/*.md` for focused import, reconciliation, audit packet, CPA, and troubleshooting guides.
- `docs/assets/screenshots/` for synthetic screenshots that are safe to publish.

The GitHub Wiki pages are generated from `docs/` by `scripts/generate_wiki_home.py` and synced by `.github/workflows/sync-wiki.yml`. The public website is maintained in the separate `salexandert/Gainz-Website` repository and should sync selected screenshots, links, and guide references from this app repo.

Do not hand-maintain a second long-form copy of the same walkthrough in the wiki or website. The generated wiki includes inline screenshots, a walkthrough, guide index, and docs publishing flow. Wiki edits for product docs should happen in `docs/` first because the next sync replaces stale wiki-only pages.

## Local Checks

Before pushing public docs or release changes, run:

```powershell
python .\scripts\generate_wiki_home.py --output-dir .\build\wiki
python -m pytest Tests
git diff --check
```

Never commit private saves, exports, source tax files, audit packets, logs, uploaded CSVs, local plans, or instance data.

## Parser Requests

Parser fixes should include tests and synthetic demo data only. Do not commit real exchange exports, tax folders, audit packets, or screenshots with private financial details.

When adding parser support, update:

- import code and tests
- `demo_data/` only if a small synthetic sample is useful
- `docs/` when the user flow or supported-source description changes
- website guide links in `salexandert/Gainz-Website` when public guidance changes
