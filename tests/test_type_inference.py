"""Regression tests for type inference and valid-SQL edge cases.

These guard the two correctness fixes in converter.py:

1. Mixed-type columns collapse to TEXT so the generated INSERTs are valid for
   every dialect (Postgres/MySQL would reject a quoted string literal placed
   into a numeric column).
2. Empty / nested-only roots emit valid SQL (or an explicit comment) instead of
   an invalid ``CREATE TABLE "x" ();`` / ``INSERT INTO "x" () VALUES ();``.
"""

from __future__ import annotations

import json
import re

import pytest

from json2sql.converter import JSONToSQLConverter
from json2sql.dialects import Dialect

NUMERIC = {"INT", "INTEGER", "DOUBLE PRECISION", "DOUBLE", "REAL"}


def column_type(out: str, col: str, dialect: Dialect) -> str | None:
    """Extract the SQL type declared for ``col`` from a CREATE TABLE in ``out``."""
    qcol = f"`{col}`" if dialect == Dialect.MYSQL else f'"{col}"'
    m = re.search(re.escape(qcol) + r"\s+(\w+(?:\([^)]*\))?)", out)
    return m.group(1) if m else None


@pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
def test_mixed_string_then_int_collapses_to_text(dialect):
    """A string followed by an int must become TEXT, not a numeric type."""
    out = JSONToSQLConverter(dialect=dialect).convert(
        json.dumps([{"k": "hello"}, {"k": 100}])
    )
    assert column_type(out, "k", dialect) == "TEXT"
    assert "'hello'" in out and "100" in out


@pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
def test_mixed_int_then_string_collapses_to_text(dialect):
    """An int followed by a string must also become TEXT (order independence)."""
    out = JSONToSQLConverter(dialect=dialect).convert(
        json.dumps([{"k": 1}, {"k": "hello"}])
    )
    assert column_type(out, "k", dialect) == "TEXT"


def test_mixed_int_then_float_collapses_to_text():
    """Two incompatible concrete types also collapse to TEXT."""
    out = JSONToSQLConverter().convert(json.dumps([{"k": 1}, {"k": 2.5}]))
    assert column_type(out, "k", Dialect.POSTGRES) == "TEXT"


@pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
def test_null_then_int_upgrades_to_int(dialect):
    """A NULL first does not pin the column to TEXT; a later int wins."""
    out = JSONToSQLConverter(dialect=dialect).convert(
        json.dumps([{"k": None}, {"k": 42}])
    )
    assert column_type(out, "k", dialect) in NUMERIC


@pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
def test_int_then_null_stays_int(dialect):
    """A trailing NULL must not downgrade an established concrete type."""
    out = JSONToSQLConverter(dialect=dialect).convert(
        json.dumps([{"k": 7}, {"k": None}])
    )
    assert column_type(out, "k", dialect) in NUMERIC


@pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
def test_all_null_column_defaults_to_text(dialect):
    """An all-NULL column resolves to TEXT rather than an unset/empty type."""
    out = JSONToSQLConverter(dialect=dialect).convert(
        json.dumps([{"k": None}, {"k": None}])
    )
    assert column_type(out, "k", dialect) == "TEXT"


@pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
def test_null_then_string_becomes_text(dialect):
    """NULL first, then a string -> a text column (not an unset numeric type).

    A NULL is "unset", so the later string wins; MySQL renders this as
    VARCHAR(255), Postgres/SQLite as TEXT. The key invariant is that it is a
    string type, never INTEGER/INT.
    """
    out = JSONToSQLConverter(dialect=dialect).convert(
        json.dumps([{"k": None}, {"k": "x"}])
    )
    assert column_type(out, "k", dialect) in {"TEXT", "VARCHAR(255)"}


def test_empty_object_root_emits_no_invalid_sql():
    """An empty object must not produce ``CREATE TABLE "data" ();``."""
    out = JSONToSQLConverter().convert(json.dumps({}))
    assert "CREATE TABLE" not in out
    assert "INSERT INTO" not in out
    # An explicit, observable comment instead of a silent empty string.
    assert out.startswith("-- ")


def test_generate_schema_empty_object_emits_comment():
    """generate_schema on an empty object returns a comment, not invalid SQL."""
    out = JSONToSQLConverter().generate_schema(json.dumps({}))
    assert "CREATE TABLE" not in out
    assert out.startswith("-- ")


@pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
def test_nested_array_only_root_keeps_child_tables_only(dialect):
    """Flatten of a root with only a nested array emits child table, no bad root."""
    out = JSONToSQLConverter(dialect=dialect, flatten=True).convert(
        json.dumps({"items": [{"x": 1}, {"x": 2}]})
    )
    assert "data_items" in out
    assert column_type(out, "x", dialect) in NUMERIC
    # The bogus empty root CREATE/INSERT must be absent.
    assert 'CREATE TABLE "data" (\n\n);' not in out
    assert "INSERT INTO \"data\" ()" not in out


def test_convert_never_emits_empty_column_list():
    """No generated statement may contain a zero-column table or insert."""
    out = JSONToSQLConverter(flatten=True).convert(
        json.dumps([{"a": 1, "b": [{"c": 2}]}, {"a": 3}])
    )
    assert "();" not in out
    assert "INSERT INTO" in out


class TestFlattenFKDetection:
    """Tests for correct FK column detection in flatten mode.

    The FK column in a child table must match the parent table's primary key
    column name and type. Previously the code preferred "name" over explicit
    ID fields like "user_id" or "users_id", causing a type mismatch.
    """

    @pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
    def test_flatten_prefers_id_over_name(self, dialect):
        """When parent has both 'id' and 'name', 'id' should be used for FK."""
        conv = JSONToSQLConverter(dialect=dialect, flatten=True)
        data = json.dumps([
            {"id": 1, "name": "Alice", "tags": [{"label": "x"}]},
            {"id": 2, "name": "Bob", "tags": [{"label": "y"}]},
        ])
        out = conv.convert(data, table_name="users")
        # FK column should be users_id (from parent's id), not users_name
        assert '"users_id"' in out or '`users_id`' in out
        assert '"users_name"' not in out and '`users_name`' not in out
        # Parent table should have id column
        assert '"id"' in out or '`id`' in out

    @pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
    def test_flatten_prefers_table_specific_id(self, dialect):
        """When parent has '{table}_id' (e.g., users_id), it should be used."""
        conv = JSONToSQLConverter(dialect=dialect, flatten=True)
        data = json.dumps([
            {"users_id": 10, "name": "Alice", "tags": [{"label": "x"}]},
            {"users_id": 20, "name": "Bob", "tags": [{"label": "y"}]},
        ])
        out = conv.convert(data, table_name="users")
        # FK column should be users_users_id (from parent's users_id)
        assert '"users_users_id"' in out or '`users_users_id`' in out
        assert '"users_name"' not in out and '`users_name`' not in out

    @pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
    def test_flatten_prefers_any_id_suffix(self, dialect):
        """When parent has a singular '*_id' (e.g., user_id), it should be used over 'name'."""
        conv = JSONToSQLConverter(dialect=dialect, flatten=True)
        data = json.dumps([
            {"user_id": 100, "name": "Alice", "tags": [{"label": "x"}]},
            {"user_id": 200, "name": "Bob", "tags": [{"label": "y"}]},
        ])
        out = conv.convert(data, table_name="users")
        # FK column should be users_user_id (from parent's user_id)
        assert '"users_user_id"' in out or '`users_user_id`' in out
        assert '"users_name"' not in out and '`users_name`' not in out
        # FK type should be numeric (matching parent's user_id type)
        if dialect == Dialect.MYSQL:
            assert "INT" in out
        else:
            assert "INTEGER" in out

    @pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
    def test_flatten_fallback_to_name_when_no_id(self, dialect):
        """When parent has no ID-like field, 'name' is used as fallback."""
        conv = JSONToSQLConverter(dialect=dialect, flatten=True)
        data = json.dumps([
            {"name": "Alice", "tags": [{"label": "x"}]},
            {"name": "Bob", "tags": [{"label": "y"}]},
        ])
        out = conv.convert(data, table_name="users")
        # FK column should be users_name (fallback)
        assert '"users_name"' in out or '`users_name`' in out
        # Parent table should have name column
        assert '"name"' in out or '`name`' in out
