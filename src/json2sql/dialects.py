"""SQL dialect definitions and formatting."""

from enum import Enum
from typing import Any


class Dialect(str, Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"


# Python type -> SQL type mapping per dialect
_TYPE_MAP = {
    Dialect.POSTGRES: {
        str: "TEXT",
        int: "INTEGER",
        float: "DOUBLE PRECISION",
        bool: "BOOLEAN",
        type(None): "TEXT",  # nullable
    },
    Dialect.MYSQL: {
        str: "VARCHAR(255)",
        int: "INT",
        float: "DOUBLE",
        bool: "TINYINT(1)",
        type(None): "TEXT",
    },
    Dialect.SQLITE: {
        str: "TEXT",
        int: "INTEGER",
        float: "REAL",
        bool: "INTEGER",
        type(None): "TEXT",
    },
}


def sql_type_for(value: Any, dialect: Dialect) -> str:
    """Infer SQL column type from a Python value."""
    if value is None:
        return _TYPE_MAP[dialect].get(str, "TEXT")
    py_type = type(value)
    if py_type is bool:  # bool must be checked before int (bool is subclass of int)
        return _TYPE_MAP[dialect][bool]
    return _TYPE_MAP[dialect].get(py_type, "TEXT")


def quote_identifier(name: str, dialect: Dialect) -> str:
    """Quote an identifier (table/column name) for the given dialect."""
    if dialect == Dialect.MYSQL:
        return f"`{name}`"
    return f'"{name}"'


def format_value(value: Any, dialect: Dialect) -> str:
    """Format a Python value as a SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        if dialect == Dialect.POSTGRES:
            return "TRUE" if value else "FALSE"
        return "1" if value else "0"
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    if isinstance(value, (int, float)):
        return str(value)
    return f"'{value}'"


def create_table_sql(
    table_name: str,
    columns: dict[str, str],
    dialect: Dialect,
) -> str:
    """Generate a CREATE TABLE statement."""
    qtable = quote_identifier(table_name, dialect)
    col_defs = []
    for col_name, col_type in columns.items():
        qcol = quote_identifier(col_name, dialect)
        col_defs.append(f"    {qcol} {col_type}")

    col_str = ",\n".join(col_defs)
    return f"CREATE TABLE {qtable} (\n{col_str}\n);"


def insert_sql(
    table_name: str,
    columns: list[str],
    rows: list[list[str]],
    dialect: Dialect,
) -> str:
    """Generate INSERT statement(s)."""
    qtable = quote_identifier(table_name, dialect)
    qcols = [quote_identifier(c, dialect) for c in columns]
    col_str = ", ".join(qcols)

    if dialect == Dialect.POSTGRES and len(rows) > 1:
        # Multi-row INSERT for PostgreSQL
        values_parts = []
        for row in rows:
            val_str = ", ".join(row)
            values_parts.append(f"    ({val_str})")
        values_str = ",\n".join(values_parts)
        return f"INSERT INTO {qtable} ({col_str})\nVALUES\n{values_str};"
    elif dialect == Dialect.MYSQL and len(rows) > 1:
        # Multi-row INSERT for MySQL
        values_parts = []
        for row in rows:
            val_str = ", ".join(row)
            values_parts.append(f"    ({val_str})")
        values_str = ",\n".join(values_parts)
        return f"INSERT INTO {qtable} ({col_str})\nVALUES\n{values_str};"
    else:
        # Single-row INSERTs (SQLite or single row)
        inserts = []
        for row in rows:
            val_str = ", ".join(row)
            inserts.append(f"INSERT INTO {qtable} ({col_str})\nVALUES ({val_str});")
        return "\n".join(inserts)
