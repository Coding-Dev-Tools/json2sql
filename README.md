# json2sql

[![GitHub stars](https://img.shields.io/github/stars/Coding-Dev-Tools/json2sql?style=social)](https://github.com/Coding-Dev-Tools/json2sql/stargazers)

Convert JSON files and datasets to SQL INSERT statements. Supports nested JSON, PostgreSQL, MySQL, and SQLite output dialects.

[![PyPI](https://img.shields.io/pypi/v/json2sql)](https://pypi.org/project/json2sql/)
[![Python](https://img.shields.io/pypi/pyversions/json2sql)](https://pypi.org/project/json2sql/)
[![License](https://img.shields.io/pypi/l/json2sql)](https://github.com/Coding-Dev-Tools/json2sql/blob/main/LICENSE)

**Why json2sql?** Moving data from JSON into a database should be one command, not a script you maintain. json2sql takes JSON files â€” flat or nested â€” and produces correct SQL INSERT statements in your dialect of choice. Nested objects are automatically flattened into relational tables. Arrays become multiple INSERT rows. Type inference handles strings, numbers, booleans, and nulls without configuration. Pipe data from stdin, specify the table name, and get clean SQL out. Zero dependencies beyond Python 3.10+ and the CLI.

## Installation

```bash
pip install json2sql
```

Or install directly from GitHub:

```bash
pip install git+https://github.com/Coding-Dev-Tools/json2sql.git
```

## Quick Start

```bash
# Basic usage â€” converts JSON to SQL INSERT statements
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
- **Zero dependencies**: Only Python 3.10+ required (typer for CLI)

## CI/CD Integration

```bash
# Generate SQL as part of a data pipeline
cat data.json | json2sql convert --dialect postgres --table events > events.sql

# Use in GitHub Actions to prepare test data
json2sql convert fixtures.json --dialect sqlite -o seed.sql
sqlite3 test.db < seed.sql
```

## Pricing

json2sql is one of eight tools in the Revenue Holdings suite. One license covers all CLI tools.

| Plan | Price | Best For |
|------|-------|----------|
| **Free** | $0 | Individual devs, OSS â€” CLI only, limited rows |
| **json2sql Individual** | **$9/mo** ($7 billed annually) | Professional devs â€” unlimited rows, batch processing |
| **Suite (all 8 tools)** | **$49/mo** ($39 billed annually) | Full Revenue Holdings toolkit â€” 40% savings |
| **Team** | **$79/mo** ($63 billed annually) | Up to 5 devs â€” API access, CI/CD integration, priority support |
| **Enterprise** | Custom | SSO, RBAC, compliance reports, dedicated support |

ðŸ”¹ **No lock-in**: CLI works fully offline on the free tier â€” no telemetry, no phone-home.
ðŸ”¹ **Annual billing**: Save 20%.

### Per-Tier Features

| Feature | Free | json2sql | Suite | Team | Enterprise |
|---------|:----:|:--------:|:-----:|:----:|:----------:|
| CLI: convert, pipe | âœ“ | âœ“ | âœ“ | âœ“ | âœ“ |
| Unlimited rows per conversion | â€” | âœ“ | âœ“ | âœ“ | âœ“ |
| Batch processing | â€” | âœ“ | âœ“ | âœ“ | âœ“ |
| Schema generation | â€” | âœ“ | âœ“ | âœ“ | âœ“ |
| API access | â€” | â€” | â€” | âœ“ | âœ“ |
| Compliance reports | â€” | â€” | â€” | â€” | âœ“ |
| RBAC | â€” | â€” | â€” | â€” | âœ“ |
| SSO / SAML / OIDC | â€” | â€” | â€” | â€” | âœ“ |
| Priority support | Community | 24h | 24h | 8h | Dedicated |

---

<p align="center">
  <sub>Part of <a href="https://coding-dev-tools.github.io/revenueholdings.dev/">Revenue Holdings</a> â€” CLI tools built by autonomous AI.</sub>
</p>

## License

MIT

