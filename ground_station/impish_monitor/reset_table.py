"""
Allows deletion of tables from the SQL database.
"""

from . import DB_NAME, HEALTH_TABLE_NAME, QUICKLOOK_TABLE_NAME, COMMAND_TABLE_NAME, connect
from .initialize_database import create_health_table, create_quicklook_table, create_command_table


CREATE = {
    HEALTH_TABLE_NAME: create_health_table,
    QUICKLOOK_TABLE_NAME: create_quicklook_table,
    COMMAND_TABLE_NAME: create_command_table,
}


def delete_table(table_name: str):
    db = connect()
    db.cursor().execute(f"DROP TABLE {table_name};")


def main():
    for table in [HEALTH_TABLE_NAME, QUICKLOOK_TABLE_NAME, COMMAND_TABLE_NAME]:
        if input(f"CONFIRM TABLE RESET ({DB_NAME}/{table}) [-y|-Y]: ").lower() == "-y":
            print(f"Resetting {table} table")
            delete_table(table)
            CREATE[table]()
        else:
            print(f"Invalid input. Doing nothing to {DB_NAME}/{table}.")


if __name__ == "__main__":
    main()
