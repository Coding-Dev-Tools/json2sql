# json2sql

[![GitHub stars](https://img.shields.io/github/stars/Coding-Dev-Tools/json2sql?style=social)](https://github.com/Coding-Dev-Tools/json2sql/stargazers)

Convert JSON files and datasets to SQL INSERT statements. Supports nested JSON, PostgreSQL, MySQL, and SQLite output dialects.

> ⭐ **Star this repo** if you work with JSON data — it helps other devs discover json2sql!

[![GitHub release](https://img.shields.io/github/v/release/Coding-Dev-Tools/json2sql?label=latest)](https://github.com/Coding-Dev-Tools/json2sql/releases)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/Coding-Dev-Tools/json2sql/blob/main/LICENSE)
|[![Open Source Alternative](https://img.shields.io/badge/Open_Source_Alternative-%E2%87%92-blue?logo=opensourceinitiative)](https://www.opensourcealternative.to/project/json2sql)
[![CI](https://github.com/Coding-Dev-Tools/json2sql/actions/workflows/ci.yml/badge.svg)](https://github.com/Coding-Dev-Tools/json2sql/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/json2sql-cli)](https://pypi.org/project/json2sql-cli/)



Real-world scenarios:
- **Seeding test databases**: Convert API response fixtures into seed data for integration tests
- **Data migrations**: Transform JSON exports from one system into INSERT statements for a new database
- **CI/CD pipelines**: Generate SQL from JSON configs as part of automated deployment
- **Analytics imports**: Convert event JSON payloads into structured SQL tables for querying

## Installation

```bash
pip install json2sql-cli
```

Or install directly from GitHub:

```bash
pip install git+https://github.com/Coding-Dev-Tools/json2sql.git
```

## Quick Start

```bash
# Basic usage — converts JSON to SQL INSERT statements
json2sql convert data.json

# Specify output dialect
json2sql convert data.json --dialect postgres
json2sql convert data.json --dialect mysql
json2sql convert data.json --dialect sqlite

# Specify output file
json2sql convert data.json -o output.sql

# Specify table name
json2sql convert data.json --table users

# Handle nested JSON (auto-flattens into relational tables)
json2sql convert nested_data.json --flatten
```

## Features

- **Nested JSON support**: Automatically flattens nested objects into separate relational tables
- **Multi-dialect output**: PostgreSQL, MySQL, SQLite INSERT syntax
- **Array of objects**: Handles JSON arrays as multiple INSERT rows
- **Type inference**: Auto-detects strings, numbers, booleans, nulls
- **Pipe support**: Read from stdin for pipeline usage
- **Minimal dependencies**: Requires Python 3.10+ with typer and rich

## CI/CD Integration

```bash
# Generate SQL as part of a data pipeline
cat data.json | json2sql convert --dialect postgres --table events > events.sql

# Use in GitHub Actions to prepare test data
json2sql convert fixtures.json --dialect sqlite -o seed.sql
sqlite3 test.db < seed.sql
```

## Pricing

json2sql is one of eleven CLI tools in the Revenue Holdings suite. One license covers all CLI tools.

| Plan | Price | Best For |
|------|-------|----------|
| **Free** | $0 | Individual devs, OSS — CLI only, limited rows |
| **json2sql Individual** | **$9/mo** ($7 billed annually) | Professional devs — unlimited rows, batch processing |
| **Suite (all 11 CLI tools)** | **$49/mo** ($39 billed annually) | Full Revenue Holdings toolkit — 40% savings |
| **Team** | **$79/mo** ($63 billed annually) | Up to 5 devs — API access, CI/CD integration, priority support |
| **Enterprise** | Custom | SSO, RBAC, compliance reports, dedicated support |

🔹 **No lock-in**: CLI works fully offline on the free tier — no telemetry, no phone-home.
🔹 **Annual billing**: Save 20%.

### Per-Tier Features

| Feature | Free | json2sql | Suite | Team | Enterprise |
|---------|:----:|:--------:|:-----:|:----:|:----------:|
| CLI: convert, pipe | ✓ | ✓ | ✓ | ✓ | ✓ |
| Unlimited rows per conversion | — | ✓ | ✓ | ✓ | ✓ |
| Batch processing | — | ✓ | ✓ | ✓ | ✓ |
| Schema generation | — | ✓ | ✓ | ✓ | ✓ |
| API access | — | — | — | ✓ | ✓ |
| Compliance reports | — | — | — | — | ✓ |
| RBAC | — | — | — | — | ✓ |
| SSO / SAML / OIDC | — | — | — | — | ✓ |
| Priority support | Community | 24h | 24h | 8h | Dedicated |

---

<p align="center">
  <sub>Part of <a href="https://coding-dev-tools.github.io/revenueholdings.dev/">Revenue Holdings</a> — CLI developer tools.</sub>
</p>

## License

MIT
