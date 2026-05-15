# Changelog

All notable changes to json2sql will be documented in this file.

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
