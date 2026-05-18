# Changelog

All notable changes to json2sql will be documented in this file.

## [Unreleased]

### Added

- CLI integration tests with comprehensive coverage (#8, #9, #10)
- Standalone dialect tests and converter edge cases (#10)
- npm wrapper (`package.json` + `cli.js`) for npm publishing
- GitHub Actions: PyPI publish workflow (release or manual dispatch)
- GitHub Actions: GitHub Pages deployment workflow
- GitHub Actions: npm publish workflow (release or manual dispatch)
- `CONTRIBUTING.md` with development setup and PR guidelines
- `SECURITY.md` with security policy
- Homebrew and Scoop install methods with bucket setup docs
- Directory listing badges: Open Source Alternative, LibHunt, Awesome Python
- Awesome DevOps submission badge (#433)
- `[project.urls]` metadata in `pyproject.toml` (Homepage, Source, Issues, Changelog)
- GitHub-based install fallback documentation
- Schema-only mode (`--schema-only` flag for CREATE TABLE only)

### Fixed

- UTF-8 encoding (mojibake) in file output
- Ruff lint warnings: E501, B904, F821, X|None syntax, `datetime.UTC` deprecation
- README install section formatting (broken Homebrew/Scoop code blocks)
- Broken PyPI badges replaced with GitHub release badge
- PyPI package name conflict — renamed to `json2sql-cli`
- `revenueholdings_license` import made optional (fixes CI failures when not installed)
- Missing `ruff` dev dependency in `pyproject.toml`
- CONTRIBUTING.md typos in lint commands (`uff` → `ruff`)
- `npm-publish.yml` removed (wrong-language workflow for Python repo)

### Changed

- CI test matrix expanded to include Python 3.13
- CI security hardened: `persist-credentials: false` on checkout steps
- CI permissions restricted to `contents: read`
- npm keywords optimized for discoverability (15 terms), npm version bumped to 0.1.1

### Docs

- README rewritten with unified pricing tables, Revenue Holdings branding
- README expanded with CI/CD integration examples and alternatives comparison
- README tool count and DevForge URLs updated
- npm install instructions added to README

## [0.1.0] — 2026-05-14

### Added

- Initial release
- JSON to SQL INSERT conversion
- Nested JSON auto-flattening into relational tables
- Multi-dialect output: PostgreSQL, MySQL, SQLite
- Array-of-objects handling as multiple INSERT rows
- Type inference for strings, numbers, booleans, nulls
- stdin pipe support
- Table name specification
- Output file support
- Python 3.10+ support, zero dependencies beyond typer
