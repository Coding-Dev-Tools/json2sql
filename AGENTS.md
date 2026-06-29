# json2sql — Agent Guide

## Repo overview
This repo converts JSON to SQL. Primary implementation is under `src/json2sql/`. CLI entrypoints live in `cli.py` and `__main__.py`.

## Commands
- Install/dev: `pip install -e .`
- Tests: `pytest`
- Lint/type checks (if configured): use tooling in `pyproject.toml`

## Do not break
- Do not remove or weaken existing tests.
- Keep public CLI behavior stable unless an issue explicitly requests changing it.
