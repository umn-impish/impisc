from . import DB_NAME, HEALTH_TABLE_NAME, connect
from .initialize_database import create_health_table


def delete_table():
    db = connect()
    db.cursor().execute(f"DROP TABLE {HEALTH_TABLE_NAME};")


def main():
    if input(f"CONFIRM TABLE RESET ({DB_NAME}/{HEALTH_TABLE_NAME}) [-y|-Y]: ").lower() == "-y":
        print("Resetting health table")
        delete_table()
        create_health_table()
    else:
        print("Invalid input. Doing nothing.")


if __name__ == "__main__":
    main()
