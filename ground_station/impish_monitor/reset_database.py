from . import DB_NAME, TABLE_NAME, connect
from .initialize_database import create_table


def delete_table():
    db = connect()
    db.cursor().execute(f"DROP TABLE {TABLE_NAME};")


def main():
    if input(f"CONFIRM TABLE RESET ({DB_NAME}/{TABLE_NAME}) [-y|-Y]: ").lower() == "-y":
        print("Resetting health database")
        delete_table()
        create_table()
    else:
        print("Invalid input. Doing nothing.")


if __name__ == "__main__":
    main()
