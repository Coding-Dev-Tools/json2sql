"""Tests for __main__.py entry point and remaining uncovered CLI paths."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

from typer.testing import CliRunner

from json2sql.cli import app
from json2sql.converter import JSONToSQLConverter

runner = CliRunner()


class TestMainModule:
    """Tests for __main__.py entry point."""

    def test_main_module_runs_convert_help(self):
        """python -m json2sql convert --help works (covers __main__.py)."""
        result = subprocess.run(
            [sys.executable, "-m", "json2sql", "convert", "--help"],
            capture_output=True, text=False,
        )
        assert result.returncode == 0
        assert b"Usage" in result.stdout


class TestCliUncovered:
    """Tests for uncovered CLI paths."""

    def test_version_command_runs(self):
        """version command prints version string."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "json2sql" in result.output
        assert "." in result.output

    def test_help_shows_commands(self):
        """Top-level help lists subcommands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in ["convert", "version"]:
            assert cmd in result.output


class TestConverterEdgeCases:
    """Edge cases for converter uncovered paths."""

    def test_type_upgrade_text_to_non_text(self):
        """When a column first has nulls then non-null values, type upgrades (converter.py:175)."""
        converter = JSONToSQLConverter()
        data = [
            {"id": 1, "score": None},
            {"id": 2, "score": 42},
        ]
        columns = converter._infer_columns(data)
        assert columns["score"] == "INTEGER"


class TestMCPCommand:
    """Tests for MCP subcommand edge cases."""

    def test_mcp_without_click_to_mcp_raises_error(self):
        """mcp subcommand without click_to_mcp shows ImportError."""
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "click_to_mcp":
                raise ImportError("No module named click_to_mcp")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", mock_import):
            result = runner.invoke(app, ["mcp"])
        assert result.exit_code != 0
        assert "click_to_mcp" in result.output.lower() or "pip install" in result.output.lower()
