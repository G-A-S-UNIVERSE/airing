# Contributing to AiRing

## Quick Start

```bash
git clone https://github.com/G-A-S-UNIVERSE/airing.git
cd airing
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your test values
pytest -v
```

## Adding a New OLT Adapter

See [docs/ADAPTER_DEVELOPMENT.md](docs/ADAPTER_DEVELOPMENT.md) for the full 6-step guide.

Each adapter lives in `src/adapters/` and must implement the `BaseOLTAdapter` interface.

## Code Style

We use `ruff` for linting and `black` for formatting:

```bash
ruff check src tests
black src tests
```

## Pull Request Process

1. Fork the repo and create a feature branch.
2. Ensure tests pass: `pytest -v --cov=src`
3. Ensure linting passes: `ruff check src tests && black --check src tests`
4. Open a PR against `main` with a clear description.
