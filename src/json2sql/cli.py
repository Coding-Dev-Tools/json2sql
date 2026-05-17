"""CLI interface for json2sql using Typer."""

import sys
from pathlib import Path
from typing import Optional

import typer

try:
    from revenueholdings_license import require_license
except ImportError:
    import warnings
    warnings.warn("revenueholdings-license not installed; license checks skipped", stacklevel=2)
    def require_license(product: str) -> None:  # type: ignore[misc]
        pass

from .converter import JSONToSQLConverter
from .dialects import Dialect

app = typer.Typer(
    name="json2sql",
    help="Convert JSON files/datasets to SQL INSERT statements.",
    no_args_is_help=True,
)


@app.command()
def convert(
    input_file: Optional[Path] = typer.Argument(
        None,
        help="Path to JSON file. Reads from stdin if not provided.",
        exists=True,
    ),
    dialect: Dialect = typer.Option(
        Dialect.POSTGRES,
        "--dialect",
        "-d",
        help="SQL dialect: postgres, mysql, sqlite",
    ),
    table: str = typer.Option(
        "data",
        "--table",
        "-t",
        help="Table name for INSERT statements.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output SQL file. Prints to stdout if not provided.",
    ),
    flatten: bool = typer.Option(
        False,
        "--flatten",
        "-f",
        help="Flatten nested JSON into relational tables.",
    ),
    schema_only: bool = typer.Option(
        False,
        "--schema-only",
        help="Generate CREATE TABLE statements only (no INSERT).",
    ),
):
    """Convert a JSON file to SQL INSERT statements."""
    require_license("json2sql")
    # Read input
    if input_file:
        json_text = input_file.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        json_text = sys.stdin.read()
    else:
        typer.echo("Error: Provide a JSON file or pipe JSON to stdin.", err=True)
        raise typer.Exit(code=1)

    converter = JSONToSQLConverter(dialect=dialect, flatten=flatten)

    try:
        if schema_only:
            result = converter.generate_schema(json_text, table_name=table)
        else:
            result = converter.convert(json_text, table_name=table)
    except Exception as e:
        typer.echo(f"Error converting JSON: {e}", err=True)
        raise typer.Exit(code=1)

    # Write output
    if output:
        output.write_text(result, encoding="utf-8")
        typer.echo(f"SQL written to {output}", err=True)
    else:
        typer.echo(result)


@app.command()
def mcp():
    """Run as an MCP (Model Context Protocol) server over stdio.

    AI coding agents (Claude Code, Cursor, etc.) use this to interact
    with json2sql tools directly.
    """
    require_license("json2sql")
    from click_to_mcp import run
    run(app)


@app.command()
def version():
    """Show version."""
    require_license("json2sql")
    from . import __version__
    typer.echo(f"json2sql {__version__}")


if __name__ == "__main__":
    app()
