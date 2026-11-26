# AiRing Example Configurations

These are **fictional** example configurations that showcase the shape of
configuration AiRing expects. Every hostname, IP, username, and password in
these files is invented.

- `config.zte.starwars.json` — ZTE C320 OLTs, themed with Star Wars planets
- `config.cdata.startrek.json` — C-Data EPON OLTs, themed with Star Trek locations

## These are examples, not secrets

If a real password ever ends up in a file under `examples/`, that's a bug:
the file should be rewritten with a fictional value. There is no expectation
of privacy or access control for anything here.

## For real deployments

Do **not** copy these files as `credentials.json` in the repo root. Instead:

1. Copy `.env.example` → `.env` at the repo root
2. Fill in real values
3. Add `.env` to your **local** `.gitignore` (the shipped one already excludes it)
4. Never commit `.env`

Runtime credentials are read from `.env` via `src.core.config.Settings`.
The JSON files here are for tests and documentation only.
