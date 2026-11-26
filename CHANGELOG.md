# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- The CLI-bridge adapter is now `GenericCLIAdapter`, living in
  `src/adapters/generic_cli_adapter.py`, and is registered under the vendor key
  `generic_cli`. **Breaking** for consumers that imported the previous class
  name or called `get_adapter()` with the previous key.
- The CLI-bridge configuration variables are now `GENERIC_CLI_MQTT_HOST`,
  `GENERIC_CLI_MQTT_PORT` and `GENERIC_CLI_API`. The previous variable names
  are no longer read — rename them in your environment or `.env`.
- Type annotations modernised to PEP 604 / PEP 585 (`Optional[X]` becomes
  `X | None`, `Dict`/`List` become `dict`/`list`). No runtime behaviour change.
- Mock inventory data now uses neutral OLT names and documentation-range IP
  addresses only.

### Removed
- Configuration blocks from `.env.example` that had no corresponding code path
  (monitoring and telemetry vendor blocks, a bot-alert block, and an
  LLM-gateway block). Every remaining variable now maps 1:1 to a field in
  `src/core/config.py`.
- Documentation references to a non-existent `audit` / `database` core module.
- The `develop` branch from the CI trigger; the pipeline now runs on `main`.

### Fixed
- CI now installs `pytest-cov`, so the coverage flags in the test job no longer
  abort the run, and `coverage.xml` is produced for the artifact upload.
- `ruff` and `black` now pass cleanly on `src` and `tests`.

## [0.1.0] - 2026-06-27

### Added
- FastAPI backend with vendor-neutral adapter pattern for multi-vendor FTTH OLTs
- HMAC-SHA256 webhook signature verification (constant-time compare)
- Prompt-injection guard (recursive payload scan)
- Idempotency deduplication (5-minute sliding window)
- Health, readiness, and metrics endpoints
- GenericCLIAdapter (HTTP CLI bridge) + ZteC320Adapter (SNMP) reference implementations
- pydantic-settings environment-driven configuration
- Docker: multi-stage Dockerfile + docker-compose
- CI: ruff + black + pytest-cov on Python 3.11/3.12
- Docs: ARCHITECTURE.md, ADAPTER_DEVELOPMENT.md
- Tests: 30 passing

### License
- MIT
