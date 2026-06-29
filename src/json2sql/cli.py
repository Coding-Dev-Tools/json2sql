"""CLI interface for json2sql using Typer."""

import os
import sys
from pathlib import Path

import typer

# Lazy imports — converter/dialects pulled on command execution
# to reduce cold start from ~340ms to ~160ms.

try:
    from revenueholdings_license import require_license
except ImportError:
    import warnings

    warnings.warn(
        "revenueholdings-license not installed; license checks skipped", stacklevel=2
    )

    def require_license(product: str) -> None:  # type: ignore[misc]
        pass


from .converter import JSONToSQLConverter
from .dialects import Dialect

_require_license_strict: bool = False

app = typer.Typer(
    name="json2sql",
    help="Convert JSON files/datasets to SQL INSERT statements.",
    no_args_is_help=True,
)


@app.callback()
def _app_callback(
    require_license_flag: bool = typer.Option(
        False,
        "--require-license",
        help=(
            "Exit with an error if revenueholdings-license is not installed "
            "or if the license check fails. "
            "Also enabled via REVENUEHOLDINGS_REQUIRE_LICENSE=1."
        ),
    ),
) -> None:
    """Convert JSON files/datasets to SQL INSERT statements."""
    global _require_license_strict
    _require_license_strict = require_license_flag or bool(
        os.environ.get("REVENUEHOLDINGS_REQUIRE_LICENSE")
    )


def _check_license(tool_name: str) -> None:
    """Check revenueholdings license; raise on failure if strict mode is enabled."""
    if os.environ.get("REVENUEHOLDINGS_LICENSE_BYPASS"):
        return
    try:
        from revenueholdings_license import require_license

        require_license(tool_name)
    except ImportError:
        if _require_license_strict:
            typer.echo(
                "Error: revenueholdings-license is not installed. "
                "Install it with: pip install revenueholdings-license",
                err=True,
            )
            raise typer.Exit(code=1) from None
    except Exception:
        if _require_license_strict:
            raise


@app.command()
def convert(
    input_file: Path | None = typer.Argument(  # noqa: B008
        None,
        help="Path to JSON file. Reads from stdin if not provided.",
        exists=True,
    ),
    dialect: str = typer.Option(  # noqa: B008
        "postgres",
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
    output: Path | None = typer.Option(  # noqa: B008
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
    _check_license("json2sql")

    # Validate dialect
    try:
        dialect_enum = Dialect(dialect)
    except ValueError:
        valid = ", ".join(d.value for d in Dialect)
        typer.echo(
            f"Error: Unknown dialect '{dialect}'. Choose from: {valid}", err=True
        )
        raise typer.Exit(code=1) from None

    # Read input
    if input_file:
        json_text = input_file.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        json_text = sys.stdin.read()
    else:
        typer.echo("Error: Provide a JSON file or pipe JSON to stdin.", err=True)
        raise typer.Exit(code=1)

    converter = JSONToSQLConverter(dialect=dialect_enum, flatten=flatten)

    try:
        if schema_only:
            result = converter.generate_schema(json_text, table_name=table)
        else:
            result = converter.convert(json_text, table_name=table)
    except Exception as e:
        typer.echo(f"Error converting JSON: {e}", err=True)
        raise typer.Exit(code=1) from e

    # Write output
    if output:
        output.write_text(result, encoding="utf-8")
        typer.echo(f"SQL written to {output}", err=True)
    else:
        typer.echo(result)


@app.command()
def mcp() -> None:
    """Run as an MCP (Model Context Protocol) server over stdio.

    AI coding agents (Claude Code, Cursor, etc.) use this to interact
    with json2sql tools directly.
    """
    _check_license("json2sql")
    try:
        from click_to_mcp import run  # type: ignore[import-untyped]
    except ImportError:
        typer.echo(
            "Error: click_to_mcp is required for MCP mode. "
            "Install it with: pip install click-to-mcp",
            err=True,
        )
        raise typer.Exit(code=1) from None
    run(app)


@app.command()
def version() -> None:
    """Show version."""
    from . import __version__

    typer.echo(f"json2sql {__version__}")


if __name__ == "__main__":
    app()
