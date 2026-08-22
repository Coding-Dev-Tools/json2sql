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
            statements.append(
                insert_sql(name, list(columns.keys()), rows, self.dialect)
            )

        result = "\n\n".join(s for s in statements if s)
        # An empty object / nested-only root legitimately produces no SQL; say
        # so explicitly instead of returning "" (avoids a silent green no-op).
        return (
            result
            if result
            else "-- No columns to generate (empty or nested-only object)."
        )

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

        statements = []
        if columns:
            statements.append(create_table_sql(table_name, columns, self.dialect))

        # Process extra tables from flattening
        self._process_flatten(objects, table_name)
        for name, cols, _ in self._extra_tables:
            statements.append(create_table_sql(name, cols, self.dialect))

        result = "\n\n".join(statements)
        return result if result else "-- No columns to generate."

    def _convert_objects(self, objects: list[dict], table_name: str) -> str:
        """Convert a list of JSON objects to SQL."""
        # When flattening, compute the full column set first so rows align
        if self.flatten:
            columns, flat_map = self._infer_columns_flattened(objects, table_name)
            # Process nested arrays into child tables, grouped by key so that
            # each nested array produces exactly ONE child table whose INSERT
            # covers every parent row's children.
            nested_groups: dict[str, tuple[list[dict], list[dict]]] = {}
            for obj in objects:
                for key, value in obj.items():
                    if (
                        isinstance(value, list)
                        and value
                        and all(isinstance(v, dict) for v in value)
                    ):
                        children, parents = nested_groups.setdefault(key, ([], []))
                        children.extend(value)
                        parents.extend([obj] * len(value))
            for key, (children, parents) in nested_groups.items():
                self._flatten_nested(table_name, key, children, parents)
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

        if not columns:
            # No scalar columns to emit (e.g. an empty object, or a root whose
            # only content is nested arrays that became child tables). Emit
            # nothing here rather than an invalid `CREATE TABLE "x" ();`.
            return ""
        parts = [create_table_sql(table_name, columns, self.dialect)]
        if rows:
            parts.append(
                insert_sql(table_name, list(columns.keys()), rows, self.dialect)
            )
        return "\n\n".join(parts)

    def _convert_primitives(self, values: list, table_name: str) -> str:
        """Convert a list of primitive values to SQL."""
        col_type = sql_type_for(values[0] if values else None, self.dialect)
        columns = {"value": col_type}
        rows = [[format_value(v, self.dialect)] for v in values]
        parts = [create_table_sql(table_name, columns, self.dialect)]
        parts.append(insert_sql(table_name, ["value"], rows, self.dialect))
        return "\n\n".join(parts)

    def _infer_type(self, value: object) -> str | None:
        """Return the SQL type for ``value``, or ``None`` when it is NULL.

        A NULL value is treated as *unset* rather than as TEXT so a column
        that first sees NULL can still take a concrete type when a non-NULL
        value arrives later (e.g. ``[null, 42]`` -> INTEGER), and an
        all-NULL column resolves to TEXT.
        """
        if value is None:
            return None
        return sql_type_for(value, self.dialect)

    def _merge_type(self, current: str | None, inferred: str) -> str:
        """Merge a previously inferred column type with a new value's type.

        Returns ``TEXT`` whenever the two types are incompatible, because TEXT
        is the only column type that is valid across Postgres/MySQL/SQLite.
        This guarantees the generated INSERTs are executable for every dialect
        instead of silently emitting a quoted string literal into a numeric
        column (invalid SQL on Postgres/MySQL).
        """
        if current is None:
            return inferred
        if current == inferred:
            return current
        return "TEXT"

    def _infer_columns(self, objects: list[dict]) -> dict[str, str]:
        """Infer column names and types from a list of objects.

        Type inference is order-independent and always yields SQL that is
        valid for every supported dialect: once a column has seen values of
        two incompatible types it collapses to TEXT.
        """
        columns: dict[str, str | None] = {}
        for obj in objects:
            for key, value in obj.items():
                inferred = self._infer_type(value)
                if key not in columns:
                    columns[key] = inferred
                elif inferred is not None:
                    columns[key] = self._merge_type(columns[key], inferred)
        # Resolve columns that never received a concrete value (all NULL) to TEXT.
        return {k: (v if v is not None else "TEXT") for k, v in columns.items()}

    def _infer_columns_flattened(
        self, objects: list[dict], table_name: str
    ) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
        """Infer columns after flattening nested objects.

        Returns:
            A tuple of (columns, flat_map) where columns maps column name -> SQL type
            and flat_map maps flattened column name -> (parent_key, sub_key) for
            resolving values during row construction.
        """
        columns: dict[str, str | None] = {}
        flat_map: dict[str, tuple[str, str]] = {}
        for obj in objects:
            for key, value in obj.items():
                if isinstance(value, dict) and self.flatten:
                    for sub_key, sub_value in value.items():
                        flat_key = f"{key}_{sub_key}"
                        inferred = self._infer_type(sub_value)
                        if flat_key not in columns:
                            columns[flat_key] = inferred
                            flat_map[flat_key] = (key, sub_key)
                        elif inferred is not None:
                            columns[flat_key] = self._merge_type(
                                columns[flat_key], inferred
                            )
                elif (
                    isinstance(value, list)
                    and value
                    and self.flatten
                    and all(isinstance(v, dict) for v in value)
                ):
                    # Skip - goes to separate table
                    pass
                else:
                    inferred = self._infer_type(value)
                    if key not in columns:
                        columns[key] = inferred
                    elif inferred is not None:
                        columns[key] = self._merge_type(columns[key], inferred)
        resolved = {k: (v if v is not None else "TEXT") for k, v in columns.items()}
        return resolved, flat_map

    def _flatten_nested(
        self,
        parent_table: str,
        key: str,
        nested_objects: list[dict],
        parent_objs: list[dict],
    ) -> None:
        """Flatten nested arrays of objects into a single child table.

        ``nested_objects`` and ``parent_objs`` are aligned lists: each child
        row links back to its own parent via the foreign key. Grouping all
        parents' children into one table avoids emitting duplicate
        ``CREATE TABLE`` statements when multiple rows carry nested arrays.
        """
        child_table = f"{parent_table}_{key}"
        columns = self._infer_columns(nested_objects)
        # Add parent reference — only if no existing column has the FK name
        parent_ref = None
        for pk in ("id", "name", parent_table + "_id"):
            if any(pk in parent_obj for parent_obj in parent_objs):
                parent_ref = pk
                break
        fk_col = f"{parent_table}_{parent_ref}" if parent_ref else None
        fk_already_exists = fk_col and fk_col in columns
        if fk_col and not fk_already_exists:
            fk_parent = next(p for p in parent_objs if parent_ref in p)
            columns = {
                fk_col: sql_type_for(fk_parent[parent_ref], self.dialect),
                **columns,
            }

        rows: list[list[str]] = []
        for nested, parent_obj in zip(nested_objects, parent_objs, strict=True):
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
        nested_groups: dict[str, tuple[list[dict], list[dict]]] = {}
        for obj in objects:
            for key, value in obj.items():
                if (
                    isinstance(value, list)
                    and value
                    and all(isinstance(v, dict) for v in value)
                ):
                    children, parents = nested_groups.setdefault(key, ([], []))
                    children.extend(value)
                    parents.extend([obj] * len(value))
        for key, (children, parents) in nested_groups.items():
            self._flatten_nested(table_name, key, children, parents)
