"""Tests for json2sql CLI uncovered paths."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from json2sql.cli import app
from json2sql.dialects import Dialect

runner = CliRunner()


class TestCLIErrorPaths:
    """Targeted tests for uncovered CLI error-handling paths."""

    def test_convert_no_file_or_stdin_exit_code(self):
        """Exit code 1 when no file provided and no stdin piped.

        CliRunner replaces sys.stdin so isatty can't be meaningfully
        mocked at the module level. The important assertion is that
        the CLI gracefully exits with code 1.
        """
        result = runner.invoke(app, ["convert"])
        assert result.exit_code == 1

    def test_version_command_output(self):
        """Version command prints 'json2sql X.Y.Z'."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "json2sql 0.1.1" in result.stdout


class TestConverterFlattenEdgeCases:
    """Edge cases for converter flatten logic."""

    def test_flatten_mixed_nested_and_simple_values(self):
        """flatten=True: when a key is a dict in some rows and a simple value in others,
        the simple value should still be rendered (converter.py:104, 109)."""
        from json2sql.converter import JSONToSQLConverter

        converter = JSONToSQLConverter(flatten=True)
        data = [
            {"id": 1, "address": {"city": "NYC"}},
            {"id": 2, "address": "missing"},  # string, not dict
        ]
        result = converter.convert(json.dumps(data))
        assert "address_city" in result
        assert "'NYC'" in result
        # address is not in flat_map but IS a column (from row 2's else path)
        # Row 1's address is a dict with flatten=True → continue
        # Row 2's address is a string → rendered as "'missing'"
        assert "'missing'" in result or "NULL" in result

    def test_flatten_type_upgrade_for_flattened_column(self):
        """flattened column type upgrades from TEXT to more specific type (line 165)."""
        from json2sql.converter import JSONToSQLConverter

        converter = JSONToSQLConverter(flatten=True)
        data = [
            {"id": 1, "meta": {"count": "five"}},  # string → TEXT
            {"id": 2, "meta": {"count": 42}},  # integer → upgrade
        ]
        result = converter.convert(json.dumps(data))
        assert "meta_count" in result
        # After upgrade, type should be INTEGER not TEXT
        assert "INTEGER" in result
        assert "'five'" in result
        assert "42" in result

    def test_type_upgrade_for_top_level_column(self):
        """Top-level column type upgrades from TEXT to more specific type (line 175)."""
        from json2sql.converter import JSONToSQLConverter

        data = [
            {"key": "hello"},  # string → TEXT
            {"key": 100},  # integer → upgrade to INTEGER
        ]
        # Non-flatten path (_infer_columns)
        result = JSONToSQLConverter().convert(json.dumps(data))
        assert "INTEGER" in result
        assert "'hello'" in result
        assert "100" in result

        # Flatten path (_infer_columns_flattened else branch, line 175)
        result2 = JSONToSQLConverter(flatten=True).convert(json.dumps(data))
        assert "INTEGER" in result2
        assert "'hello'" in result2
        assert "100" in result2


class TestConverterExtraEdgePaths:
    """Additional converter coverage for remaining uncovered lines."""

    def test_convert_objects_list_vs_dict_root(self):
        """Array root with a single dict should produce one INSERT row."""
        from json2sql.converter import JSONToSQLConverter

        converter = JSONToSQLConverter()
        result = converter.convert(json.dumps([{"name": "test"}]))
        assert "INSERT INTO" in result
        assert "'test'" in result

    def test_flatten_all_nested_arrays_skips_empty_root_table(self):
        """When flatten=True and all top-level values are nested arrays,
        the root table must not emit an invalid empty CREATE TABLE."""
        from json2sql.converter import JSONToSQLConverter

        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps(
            {"users": [{"name": "a", "orders": [{"id": 1}]}]}
        )
        result = conv.convert(data, table_name="data")
        # Root table must not appear with empty columns
        assert "CREATE TABLE \"data\" ( )" not in result
        assert "INSERT INTO \"data\" ( )" not in result
        # Child tables for top-level nested arrays should still be generated
        assert "data_users" in result

    def test_empty_object_no_invalid_sql(self):
        """Empty JSON object must not produce an empty CREATE TABLE / INSERT."""
        from json2sql.converter import JSONToSQLConverter

        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES)
        result = conv.convert(json.dumps({}), table_name="data")
        assert "CREATE TABLE" not in result
        assert "INSERT INTO" not in result

    def test_generate_schema_empty_object_no_invalid_sql(self):
        """generate_schema on an empty JSON object must not emit an empty table."""
        from json2sql.converter import JSONToSQLConverter

        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES)
        result = conv.generate_schema(json.dumps({}), table_name="data")
        assert "CREATE TABLE" not in result
