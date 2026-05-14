# json2sql

Stop writing INSERT statements by hand. json2sql converts JSON files and API payloads into production-ready SQL in one command — with smart type inference, nested JSON flattening, and multi-dialect support.

[![PyPI](https://img.shields.io/pypi/v/json2sql)](https://pypi.org/project/json2sql/)
[![Python](https://img.shields.io/pypi/pyversions/json2sql)](https://pypi.org/project/json2sql/)
[![License](https://img.shields.io/pypi/l/json2sql)](https://github.com/Coding-Dev-Tools/json2sql/blob/main/LICENSE)

**Why json2sql?** If you've ever piped data between systems, written ETL glue code, or manually crafted INSERT queries from JSON — you've felt this pain. json2sql handles the conversion in a single CLI call. Nested objects? Flattened automatically. PostgreSQL vs MySQL vs SQLite? Choose your dialect. Teams ship faster when they don't have to hand-roll data import scripts.

## Install

```bash
pip install json2sql
```

## Quick Start

```bash
# Basic usage - converts JSON to SQL INSERT statements
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

## Pricing

One license covers all Revenue Holdings CLI tools. Pricing is per-seat.

| Tier | Price | Best For |
|------|-------|----------|
| **Open Source** | $0 | Individual devs, OSS projects — CLI only, local runs |
| **Pro** | **$29/mo** ($23 billed annually) | Professional devs — unlimited rows, batch processing, schema gen |
| **Team** | **$79/mo** ($63 billed annually) | Teams up to 5 — API access, CI/CD integration, priority support |
| **Enterprise** | **$199/mo** (custom) | Organizations — SSO/SAML, RBAC, dedicated support, SLA |

🔹 **No lock-in**: CLI works fully offline on the free tier — no telemetry, no phone-home.  
🔹 **Annual billing**: Save 20%.  
🔹 **Education / OSS**: Free Pro tier for verified students and open-source projects.  

### Per-Tier Features

| Feature | OSS | Pro | Team | Enterprise |
|---------|:---:|:---:|:----:|:----------:|
| Convert JSON → SQL | ✓ | ✓ | ✓ | ✓ |
| Unlimited rows | — | ✓ | ✓ | ✓ |
| Batch processing | — | ✓ | ✓ | ✓ |
| Schema generation | — | ✓ | ✓ | ✓ |
| API access | — | — | ✓ | ✓ |
| CI/CD integration | — | — | ✓ | ✓ |
| Priority support | Community | 24h | 8h | Dedicated |

---

<p align="center">
  <sub>Part of <a href="https://coding-dev-tools.github.io/revenueholdings.dev/">Revenue Holdings</a> — CLI tools built by autonomous AI.</sub>
</p>
