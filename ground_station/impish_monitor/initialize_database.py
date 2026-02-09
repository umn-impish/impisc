from mysql.connector.abstracts import MySQLCursorAbstract

from . import DB_NAME, TABLE_NAME, COLUMNS, connect


def create_db():
    db = connect(database=None)
    _ = db.cursor().execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    db.close()


def create_table():
    cols: dict[str, str] = COLUMNS
    db = connect()
    try:
        cursor: MySQLCursorAbstract = db.cursor()
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {TABLE_NAME} (id INT AUTO_INCREMENT PRIMARY KEY);"
        )
        query = """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """
        for col_name, type_ in cols.items():
            cursor.execute(query, (TABLE_NAME, col_name))
            result = cursor.fetchone()
            if result[0] == 0:
                alter_query = f"ALTER TABLE `{TABLE_NAME}` ADD `{col_name}` {type_}"
                cursor.execute(alter_query)
                db.commit()
                print(
                    f"Column '{col_name}' added to table '{TABLE_NAME}' successfully."
                )
            else:
                print(
                    f"Column '{col_name}' already exists in table '{TABLE_NAME}'. No action needed."
                )
    finally:
        _ = cursor.close()
        db.close()


def main():
    create_db()
    create_table()


if __name__ == "__main__":
    main()
