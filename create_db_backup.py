from pathlib import Path

from db import DataBase
from db_api import DB_ROOT
from test_db import DB_BACKUP_ROOT, delete_files, create_students_table


def create_db_backup() -> Path:
    DB_BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    delete_files(DB_BACKUP_ROOT)
    db = DataBase()
    create_students_table(db, 100)
    for path in DB_ROOT.iterdir():
        path.rename(DB_BACKUP_ROOT / path.name)
    return DB_BACKUP_ROOT


if __name__ == '__main__':
    create_db_backup()
