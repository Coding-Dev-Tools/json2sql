# json2sql

Convert JSON files/datasets to SQL INSERT statements. Supports nested JSON (flattens to relational tables), PostgreSQL, MySQL, and SQLite output dialects.

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

## Revenue

- **Free tier**: Up to 1,000 rows per conversion
- **Pro tier** ($19/mo): Unlimited rows, batch processing, schema generation
- **Team tier** ($49/mo): API access, CI/CD integration, priority support
