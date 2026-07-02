# json2sql — Agent Guide

## Repo overview
This repo converts JSON to SQL. Primary implementation is under `src/json2sql/`. CLI entrypoints live in `cli.py` and `__main__.py`.

## Commands
- Install/dev: `pip install -e ".[dev]"`
- Tests: `pytest tests/ -v`
- Lint: `ruff check src/ tests/`
- Format: `ruff format src/ tests/`
- Type check: `mypy src/` (if configured)

## CI/CD
- **CI** (`.github/workflows/ci.yml`): Tests on Python 3.10-3.13 + ruff lint
- **Auto Code Review** (`.github/workflows/auto-code-review.yml`): Reusable org workflow
- **Pages** (`.github/workflows/pages.yml`): Deploy docs to GitHub Pages
- **Publish** (`.github/workflows/publish.yml`): PyPI publish on tags

## Agent workflow
1. `git checkout main && git pull origin main`
2. `git checkout -b improve/json2sql-<YYYYMMDD>`
3. Make changes (max 50 lines per run)
4. `ruff check src/ tests/ && ruff format src/ tests/`
5. `pytest tests/ -v` — ensure all tests pass
6. `git add -A && git commit -m "improve: <description>"`
7. `git push origin improve/json2sql-<YYYYMMDD>`
8. `gh pr create --title "improve: <description>" --body "Automated improvement by dev-engineer." --repo Coding-Dev-Tools/json2sql`

## Do not break
- Do not remove or weaken existing tests.
- Keep public CLI behavior stable unless an issue explicitly requests changing it.
- Do not change the `convert()` function signature or return type.
- Keep lazy imports inside `convert()` to preserve cold-start optimization.

## Business context
- Part of **Coding-Dev-Tools** under **Revenue Holdings**
- Revenue Holdings north star: "Generate revenue through CLI tools, SaaS products, and automated operations."
- This is a Tier 2 repo (developer tool / CLI utility)
