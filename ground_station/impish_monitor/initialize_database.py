"""
Some functions for initializing the ground station database and associated
tables: system health and science quicklook.
"""

from collections import OrderedDict

from mysql.connector.abstracts import MySQLCursorAbstract

from . import (
    DB_NAME,
    HEALTH_TABLE_NAME,
    HEALTH_COLUMNS,
    QUICKLOOK_TABLE_NAME,
    QUICKLOOK_COLUMNS,
    connect,
)


def create_db():
    """Create the SQL database, if it doesn't exist.
    Does nothing if the database already exists.
    """
    db = connect(database=None)
    _ = db.cursor().execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    db.close()


def add_table_cols(table_name: str, cols: OrderedDict[str, str]):
    """Create a new table, if it doesn't exist. Checks if the column
    already exists and adds a new column if it doesn't.
    """
    db = connect()
    try:
        cursor: MySQLCursorAbstract = db.cursor()
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} (unix_timestamp INTEGER PRIMARY KEY);"
        )
        query = """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """
        for col_name, type_ in cols.items():
            cursor.execute(query, (table_name, col_name))
            result = cursor.fetchone()
            if result[0] == 0:
                alter_query = f"ALTER TABLE `{table_name}` ADD `{col_name}` {type_}"
                cursor.execute(alter_query)
                db.commit()
                print(
                    f"Column '{col_name}' added to table '{table_name}' successfully."
                )
            else:
                print(
                    f"Column '{col_name}' already exists in table '{table_name}'. No action needed."
                )
    finally:
        _ = cursor.close()
        db.close()


def create_health_table():
    add_table_cols(HEALTH_TABLE_NAME, HEALTH_COLUMNS)


def create_quicklook_table():
    add_table_cols(QUICKLOOK_TABLE_NAME, QUICKLOOK_COLUMNS)


def main():
    create_db()
    create_health_table()
    create_quicklook_table()


if __name__ == "__main__":
    main()
