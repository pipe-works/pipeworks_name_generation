"""
Database query functions for corpus database viewer.

All functions provide read-only access to the SQLite database.
"""

import sqlite3
from pathlib import Path
from typing import Any


def _get_connection(db_path: Path) -> sqlite3.Connection:
    """
    Get a read-only database connection.

    Parameters
    ----------
    db_path : Path
        Path to SQLite database file

    Returns
    -------
    sqlite3.Connection
        Database connection with row factory for dict-like access

    Raises
    ------
    FileNotFoundError
        If database file does not exist
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    # Open in read-only mode with URI parameter
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert sqlite3.Row to dictionary."""
    return {key: row[key] for key in row.keys()}


def get_tables_list(db_path: Path) -> list[dict[str, str]]:
    """
    Get list of all tables in the database.

    Parameters
    ----------
    db_path : Path
        Path to SQLite database file

    Returns
    -------
    list[dict[str, str]]
        List of tables, each with 'name' and 'type' keys

    Examples
    --------
    >>> tables = get_tables_list(Path("data/raw/syllable_extractor.db"))
    >>> for table in tables:
    ...     print(table['name'])
    """
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name, type FROM sqlite_master WHERE type='table' ORDER BY name")

    tables = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()

    return tables


def get_table_schema(db_path: Path, table_name: str) -> dict[str, Any]:
    """
    Get schema information for a specific table.

    Parameters
    ----------
    db_path : Path
        Path to SQLite database file
    table_name : str
        Name of the table to inspect

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        - 'columns': List of column info dicts (cid, name, type, notnull, dflt_value, pk)
        - 'indexes': List of index info dicts with nested column information
        - 'create_sql': Original CREATE TABLE statement

    Examples
    --------
    >>> schema = get_table_schema(Path("data/raw/syllable_extractor.db"), "runs")
    >>> print(schema['columns'])
    >>> print(schema['create_sql'])
    """
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    # Get column information
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [_row_to_dict(row) for row in cursor.fetchall()]

    # Get indexes
    cursor.execute(f"PRAGMA index_list({table_name})")
    indexes = []
    for idx_row in cursor.fetchall():
        idx_dict = _row_to_dict(idx_row)
        cursor.execute(f"PRAGMA index_info({idx_dict['name']})")
        idx_dict["columns"] = [_row_to_dict(col) for col in cursor.fetchall()]
        indexes.append(idx_dict)

    # Get CREATE TABLE statement
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    result = cursor.fetchone()
    create_sql = result[0] if result else ""

    conn.close()

    return {"columns": columns, "indexes": indexes, "create_sql": create_sql}


def get_table_data(
    db_path: Path,
    table_name: str,
    page: int = 1,
    limit: int = 50,
    sort_by: str = "",
    sort_order: str = "ASC",
) -> dict[str, Any]:
    """
    Get paginated data from a table.

    Parameters
    ----------
    db_path : Path
        Path to SQLite database file
    table_name : str
        Name of the table to query
    page : int, optional
        Page number (1-indexed), by default 1
    limit : int, optional
        Number of rows per page, by default 50
    sort_by : str, optional
        Column name to sort by, by default "" (no sorting)
    sort_order : str, optional
        Sort order "ASC" or "DESC", by default "ASC"

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        - 'rows': List of row data as dicts
        - 'total': Total number of rows in table
        - 'page': Current page number
        - 'limit': Rows per page
        - 'total_pages': Total number of pages

    Examples
    --------
    >>> data = get_table_data(
    ...     Path("data/raw/syllable_extractor.db"),
    ...     "runs",
    ...     page=1,
    ...     limit=10,
    ...     sort_by="run_timestamp",
    ...     sort_order="DESC"
    ... )
    >>> print(f"Showing page {data['page']} of {data['total_pages']}")
    >>> for row in data['rows']:
    ...     print(row)
    """
    # Validate sort order
    if sort_order.upper() not in ["ASC", "DESC"]:
        sort_order = "ASC"

    offset = (page - 1) * limit

    conn = _get_connection(db_path)
    cursor = conn.cursor()

    # Get total count
    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")  # nosec B608
    total = cursor.fetchone()["count"]

    # Build query with optional sorting
    query = f"SELECT * FROM {table_name}"  # nosec B608
    if sort_by:
        # Basic SQL injection prevention: validate column name exists
        cursor.execute(f"PRAGMA table_info({table_name})")
        valid_columns = [col["name"] for col in cursor.fetchall()]
        if sort_by in valid_columns:
            query += f" ORDER BY {sort_by} {sort_order}"

    query += f" LIMIT {limit} OFFSET {offset}"

    cursor.execute(query)
    rows = [_row_to_dict(row) for row in cursor.fetchall()]

    conn.close()

    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return {
        "rows": rows,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


def get_row_count(db_path: Path, table_name: str) -> int:
    """
    Get total number of rows in a table.

    Parameters
    ----------
    db_path : Path
        Path to SQLite database file
    table_name : str
        Name of the table

    Returns
    -------
    int
        Number of rows in the table

    Examples
    --------
    >>> count = get_row_count(Path("data/raw/syllable_extractor.db"), "runs")
    >>> print(f"Total runs: {count}")
    """
    conn = _get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")  # nosec B608
    result = cursor.fetchone()
    count: int = int(result["count"])
    conn.close()
    return count
