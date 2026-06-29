"""Core JSON-to-SQL conversion logic."""

import json

from .dialects import (
    Dialect,
    create_table_sql,
    format_value,
    insert_sql,
    sql_type_for,
)


class JSONToSQLConverter:
    """Convert JSON data to SQL INSERT statements."""

    def __init__(self, dialect: Dialect = Dialect.POSTGRES, flatten: bool = False):
        self.dialect = dialect
        self.flatten = flatten
        self._extra_tables: list[tuple[str, dict[str, str], list[list[str]]]] = []

    def convert(self, json_text: str, table_name: str = "data") -> str:
        """Convert JSON text to SQL statements."""
        data = json.loads(json_text)
        statements: list[str] = []
        self._extra_tables = []

        if isinstance(data, list):
            # Array of objects -> multiple rows
            if not data:
                return "-- Empty JSON array, no SQL generated."
            if isinstance(data[0], dict):
                statements.append(self._convert_objects(data, table_name))
            else:
                # Array of primitives -> single column
                statements.append(self._convert_primitives(data, table_name))
        elif isinstance(data, dict):
            # Single object -> one row
            statements.append(self._convert_objects([data], table_name))
        else:
            raise ValueError(f"Unsupported JSON root type: {type(data).__name__}")

        # Add any extra tables from flattening
        for name, columns, rows in self._extra_tables:
            statements.insert(0, create_table_sql(name, columns, self.dialect))
            statements.append(insert_sql(name, list(columns.keys()), rows, self.dialect))

        return "\n\n".join(statements)

    def generate_schema(self, json_text: str, table_name: str = "data") -> str:
        """Generate only CREATE TABLE statements from JSON data."""
        data = json.loads(json_text)
        self._extra_tables = []

        if isinstance(data, list) and data and isinstance(data[0], dict):
            objects = data
        elif isinstance(data, dict):
            objects = [data]
        else:
            objects = []

        if objects:
            if self.flatten:
                columns, _ = self._infer_columns_flattened(objects, table_name)
            else:
                columns = self._infer_columns(objects)
        else:
            columns = {"value": "TEXT"}

        statements = [create_table_sql(table_name, columns, self.dialect)]

        # Process extra tables from flattening
        self._process_flatten(objects, table_name)
        for name, cols, _ in self._extra_tables:
            statements.append(create_table_sql(name, cols, self.dialect))

        return "\n\n".join(statements)

    def _convert_objects(self, objects: list[dict], table_name: str) -> str:
        """Convert a list of JSON objects to SQL."""
        # When flattening, compute the full column set first so rows align
        if self.flatten:
            columns, flat_map = self._infer_columns_flattened(objects, table_name)
            # Process nested arrays into child tables
            for obj in objects:
                for key, value in obj.items():
                    if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
                        self._flatten_nested(table_name, key, value, obj)
        else:
            columns = self._infer_columns(objects)
            flat_map = {}
        rows: list[list[str]] = []

        for obj in objects:
            row: list[str] = []
            for col_name in columns:
                if col_name in flat_map:
                    # Flattened key — resolve from nested dict
                    parent_key, sub_key = flat_map[col_name]
                    value = obj.get(parent_key)
                    if isinstance(value, dict):
                        row.append(format_value(value.get(sub_key), self.dialect))
                    else:
                        row.append(format_value(None, self.dialect))
                else:
                    raw = obj.get(col_name)
                    if self.flatten and isinstance(raw, dict):
                        # Nested object already handled via flattened keys above
                        continue
                    else:
                        row.append(format_value(raw, self.dialect))
            rows.append(row)

        parts = [create_table_sql(table_name, columns, self.dialect)]
        if rows:
            parts.append(insert_sql(table_name, list(columns.keys()), rows, self.dialect))
        return "\n\n".join(parts)

    def _convert_primitives(self, values: list, table_name: str) -> str:
        """Convert a list of primitive values to SQL."""
        col_type = sql_type_for(values[0] if values else None, self.dialect)
        columns = {"value": col_type}
        rows = [[format_value(v, self.dialect)] for v in values]
        parts = [create_table_sql(table_name, columns, self.dialect)]
        parts.append(insert_sql(table_name, ["value"], rows, self.dialect))
        return "\n\n".join(parts)

    def _infer_columns(self, objects: list[dict]) -> dict[str, str]:
        """Infer column names and types from a list of objects."""
        columns: dict[str, str] = {}
        for obj in objects:
            for key, value in obj.items():
                if key not in columns:
                    columns[key] = sql_type_for(value, self.dialect)
                elif value is not None:
                    # Upgrade type if we find a non-null value
                    inferred = sql_type_for(value, self.dialect)
                    if columns[key] == "TEXT" and inferred != "TEXT":
                        columns[key] = inferred
        return columns

    def _infer_columns_flattened(
        self, objects: list[dict], table_name: str
    ) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
        """Infer columns after flattening nested objects.

        Returns:
            A tuple of (columns, flat_map) where columns maps column name -> SQL type
            and flat_map maps flattened column name -> (parent_key, sub_key) for
            resolving values during row construction.
        """
        columns: dict[str, str] = {}
        flat_map: dict[str, tuple[str, str]] = {}
        for obj in objects:
            for key, value in obj.items():
                if isinstance(value, dict) and self.flatten:
                    for sub_key, sub_value in value.items():
                        flat_key = f"{key}_{sub_key}"
                        if flat_key not in columns:
                            columns[flat_key] = sql_type_for(sub_value, self.dialect)
                            flat_map[flat_key] = (key, sub_key)
                        elif sub_value is not None:
                            inferred = sql_type_for(sub_value, self.dialect)
                            if columns[flat_key] == "TEXT" and inferred != "TEXT":
                                columns[flat_key] = inferred
                elif isinstance(value, list) and value and self.flatten and all(isinstance(v, dict) for v in value):
                    # Skip - goes to separate table
                    pass
                else:
                    if key not in columns:
                        columns[key] = sql_type_for(value, self.dialect)
                    elif value is not None:
                        inferred = sql_type_for(value, self.dialect)
                        if columns[key] == "TEXT" and inferred != "TEXT":
                            columns[key] = inferred
        return columns, flat_map

    def _flatten_nested(
        self,
        parent_table: str,
        key: str,
        nested_objects: list[dict],
        parent_obj: dict,
    ) -> None:
        """Flatten a nested array of objects into a separate table."""
        child_table = f"{parent_table}_{key}"
        columns = self._infer_columns(nested_objects)
        # Add parent reference — only if no existing column has the FK name
        parent_ref = None
        for pk in ("id", "name", parent_table + "_id"):
            if pk in parent_obj:
                parent_ref = pk
                break
        fk_col = f"{parent_table}_{parent_ref}" if parent_ref else None
        fk_already_exists = fk_col and fk_col in columns
        if fk_col and not fk_already_exists:
            columns = {fk_col: sql_type_for(parent_obj[parent_ref], self.dialect), **columns}

        rows: list[list[str]] = []
        for nested in nested_objects:
            row: list[str] = []
            for col_name in columns:
                if col_name == fk_col and not fk_already_exists:
                    row.append(format_value(parent_obj.get(parent_ref), self.dialect))
                else:
                    row.append(format_value(nested.get(col_name), self.dialect))
            rows.append(row)

        self._extra_tables.append((child_table, columns, rows))

    def _process_flatten(self, objects: list, table_name: str) -> None:
        """Process flattening for schema generation."""
        if not self.flatten:
            return
        if not objects or not isinstance(objects[0], dict):
            return
        for obj in objects:
            for key, value in obj.items():
                if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
                    self._flatten_nested(table_name, key, value, obj)
