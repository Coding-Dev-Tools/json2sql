"""Standalone tests for json2sql dialects module."""
import pytest
from json2sql.dialects import (
    Dialect,
    sql_type_for,
    quote_identifier,
    format_value,
    create_table_sql,
    insert_sql,
)


# --- Dialect enum ---

class TestDialectEnum:
    """Dialect enum values and membership."""

    def test_postgres_value(self):
        assert Dialect.POSTGRES == "postgres"

    def test_mysql_value(self):
        assert Dialect.MYSQL == "mysql"

    def test_sqlite_value(self):
        assert Dialect.SQLITE == "sqlite"

    def test_all_members(self):
        assert set(Dialect) == {Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE}


# --- sql_type_for ---

class TestSQLTypeFor:
    """Python type → SQL type mapping per dialect."""

    @pytest.mark.parametrize("dialect", [Dialect.POSTGRES, Dialect.MYSQL, Dialect.SQLITE])
    def test_string_type(self, dialect):
        assert "TEXT" in sql_type_for("hello", dialect).upper() or "VARCHAR" in sql_type_for("hello", dialect).upper()

    def test_postgres_int(self):
        assert sql_type_for(42, Dialect.POSTGRES) == "INTEGER"

    def test_mysql_int(self):
        assert sql_type_for(42, Dialect.MYSQL) == "INT"

    def test_sqlite_int(self):
        assert sql_type_for(42, Dialect.SQLITE) == "INTEGER"

    def test_postgres_float(self):
        assert sql_type_for(3.14, Dialect.POSTGRES) == "DOUBLE PRECISION"

    def test_mysql_float(self):
        assert sql_type_for(3.14, Dialect.MYSQL) == "DOUBLE"

    def test_sqlite_float(self):
        assert sql_type_for(3.14, Dialect.SQLITE) == "REAL"

    def test_postgres_bool(self):
        assert sql_type_for(True, Dialect.POSTGRES) == "BOOLEAN"

    def test_mysql_bool(self):
        assert sql_type_for(False, Dialect.MYSQL) == "TINYINT(1)"

    def test_sqlite_bool(self):
        assert sql_type_for(True, Dialect.SQLITE) == "INTEGER"

    def test_none_type(self):
        # None maps to the string type of each dialect
        for dialect in Dialect:
            result = sql_type_for(None, dialect)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_unknown_type(self):
        # Unrecognized type falls back to TEXT
        assert sql_type_for(b"bytes", Dialect.POSTGRES) == "TEXT"

    def test_bool_before_int_check(self):
        # bool is subclass of int; must return bool type, not int
        assert sql_type_for(True, Dialect.POSTGRES) == "BOOLEAN"
        assert sql_type_for(True, Dialect.POSTGRES) != "INTEGER"


# --- quote_identifier ---

class TestQuoteIdentifier:
    """Identifier quoting per dialect."""

    def test_mysql_backtick(self):
        assert quote_identifier("users", Dialect.MYSQL) == "`users`"

    def test_postgres_double_quote(self):
        assert quote_identifier("users", Dialect.POSTGRES) == '"users"'

    def test_sqlite_double_quote(self):
        assert quote_identifier("users", Dialect.SQLITE) == '"users"'

    def test_special_chars_mysql(self):
        assert quote_identifier("group", Dialect.MYSQL) == "`group`"

    def test_special_chars_postgres(self):
        assert quote_identifier("group", Dialect.POSTGRES) == '"group"'

    def test_empty_name(self):
        for dialect in Dialect:
            result = quote_identifier("", dialect)
            assert len(result) >= 2


# --- format_value ---

class TestFormatValue:
    """Python value → SQL literal formatting."""

    def test_null(self):
        for dialect in Dialect:
            assert format_value(None, dialect) == "NULL"

    def test_postgres_true(self):
        assert format_value(True, Dialect.POSTGRES) == "TRUE"

    def test_postgres_false(self):
        assert format_value(False, Dialect.POSTGRES) == "FALSE"

    def test_mysql_true(self):
        assert format_value(True, Dialect.MYSQL) == "1"

    def test_mysql_false(self):
        assert format_value(False, Dialect.MYSQL) == "0"

    def test_sqlite_true(self):
        assert format_value(True, Dialect.SQLITE) == "1"

    def test_sqlite_false(self):
        assert format_value(False, Dialect.SQLITE) == "0"

    def test_string_simple(self):
        assert format_value("hello", Dialect.POSTGRES) == "'hello'"

    def test_string_with_single_quote(self):
        assert format_value("it's a test", Dialect.POSTGRES) == "'it''s a test'"

    def test_string_with_double_quotes(self):
        assert format_value('say "hi"', Dialect.POSTGRES) == """'say "hi"'"""

    def test_integer(self):
        assert format_value(42, Dialect.POSTGRES) == "42"

    def test_negative_integer(self):
        assert format_value(-5, Dialect.MYSQL) == "-5"

    def test_float(self):
        assert format_value(3.14, Dialect.POSTGRES) == "3.14"

    def test_zero(self):
        assert format_value(0, Dialect.SQLITE) == "0"

    def test_empty_string(self):
        assert format_value("", Dialect.POSTGRES) == "''"


# --- create_table_sql ---

class TestCreateTableSQL:
    """CREATE TABLE statement generation."""

    def test_single_column(self):
        columns = {"name": "TEXT"}
        sql = create_table_sql("users", columns, Dialect.POSTGRES)
        assert sql.startswith("CREATE TABLE")
        assert '"users"' in sql
        assert '"name" TEXT' in sql
        assert sql.endswith(";")

    def test_multiple_columns(self):
        columns = {"id": "INTEGER", "name": "TEXT", "active": "BOOLEAN"}
        sql = create_table_sql("users", columns, Dialect.POSTGRES)
        assert sql.count('"') >= 6  # table + 3 columns each double-quoted
        assert "INTEGER" in sql
        assert "TEXT" in sql
        assert "BOOLEAN" in sql

    def test_mysql_backtick_quoting(self):
        columns = {"id": "INT"}
        sql = create_table_sql("users", columns, Dialect.MYSQL)
        assert "`users`" in sql
        assert "`id`" in sql

    def test_sqlite(self):
        columns = {"value": "TEXT"}
        sql = create_table_sql("data", columns, Dialect.SQLITE)
        assert '"data"' in sql
        assert '"value" TEXT' in sql


# --- insert_sql ---

class TestInsertSQL:
    """INSERT statement generation."""

    def test_postgres_single_row(self):
        sql = insert_sql("users", ["name"], [["'Alice'"]], Dialect.POSTGRES)
        assert sql.startswith("INSERT INTO")
        assert '"users"' in sql
        assert "'Alice'" in sql

    def test_postgres_multi_row(self):
        """PostgreSQL uses multi-row VALUES syntax for >1 rows."""
        rows = [["'Alice'"], ["'Bob'"]]
        sql = insert_sql("users", ["name"], rows, Dialect.POSTGRES)
        assert sql.startswith("INSERT INTO")
        assert "VALUES" in sql
        # Should be a single statement with two value tuples
        assert sql.count("VALUES") == 1
        assert "'Alice'" in sql
        assert "'Bob'" in sql

    def test_mysql_multi_row(self):
        """MySQL multi-row VALUES."""
        rows = [["1"], ["2"]]
        sql = insert_sql("items", ["id"], rows, Dialect.MYSQL)
        assert "VALUES" in sql
        assert "1" in sql
        assert "2" in sql
        assert sql.count("VALUES") == 1

    def test_sqlite_single_row_per_statement(self):
        """SQLite uses one INSERT per row (multi-row not supported)."""
        rows = [["'Alice'"], ["'Bob'"]]
        sql = insert_sql("users", ["name"], rows, Dialect.SQLITE)
        # SQLite generates individual INSERT statements
        assert sql.count("INSERT INTO") == 2
        assert "VALUES" in sql
        assert "'Alice'" in sql
        assert "'Bob'" in sql

    def test_sqlite_single_row(self):
        sql = insert_sql("users", ["name"], [["'Alice'"]], Dialect.SQLITE)
        assert sql.startswith("INSERT INTO")
        assert sql.count("INSERT INTO") == 1

    def test_multi_column_postgres(self):
        rows = [["1", "'Alice'"], ["2", "'Bob'"]]
        sql = insert_sql("users", ["id", "name"], rows, Dialect.POSTGRES)
        assert '"id"' in sql
        assert '"name"' in sql
        assert "'Alice'" in sql
        assert "'Bob'" in sql

    def test_mysql_quoting(self):
        rows = [["1"]]
        sql = insert_sql("items", ["id"], rows, Dialect.MYSQL)
        assert "`items`" in sql
        assert "`id`" in sql
