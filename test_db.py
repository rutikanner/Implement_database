import datetime as dt
import shutil
import time
from functools import partial
from pathlib import Path
from typing import Generator

import pytest


from db import DataBase
from db_api import DBField, SelectionCriteria, DB_ROOT, DBTable

DB_BACKUP_ROOT = DB_ROOT.parent / (DB_ROOT.name + '_backup')
STUDENT_FIELDS = [DBField('ID', int), DBField('First', str),
                  DBField('Last', str), DBField('Birthday', dt.datetime)]


def delete_files(folder: Path):
    for path in Path(folder).iterdir():
        if path.is_dir():  # No coverage when folder is empty
            delete_files(path)
            path.rmdir()
        else:
            path.unlink()  # No coverage when folder is empty


def get_folder_size(folder: Path) -> int:
    return sum(f.stat().st_size for f in folder.glob('**/*') if f.is_file())


db_size = partial(get_folder_size, DB_ROOT)


def create_students_table(db: DataBase, num_students: int = 0) -> DBTable:
    table = db.create_table('Students', STUDENT_FIELDS, 'ID')
    for i in range(num_students):
        add_student(table, i)
    return table


def add_student(table: DBTable, index: int, **kwargs) -> None:
    info = dict(
        ID=1_000_000 + index,
        First=f'John{index}',
        Last=f'Doe{index}',
        # Birthday=dt.datetime(2000, 2, 1) + dt.timedelta(days=index)
    )
    # info.update(**kwargs)
    table.insert_record(info)


@pytest.fixture(scope='function')
def new_db() -> Generator[DataBase, None, None]:
    db = DataBase()
    for table in db.get_tables_names():
        db.delete_table(table)
    delete_files(DB_ROOT)
    yield db


@pytest.fixture(scope='session')
def backup_db() -> Generator[Path, None, None]:
    yield DB_BACKUP_ROOT


def test_reload_from_backup(backup_db: Path) -> None:
    """This test requires preparing the backup by calling create_db_backup()"""
    delete_files(DB_ROOT)
    DB_ROOT.rmdir()
    shutil.copytree(str(backup_db), str(DB_ROOT))
    db = DataBase()
    assert db.num_tables() == 1
    assert db.get_tables_names() == ['Students']
    students = db.get_table('Students')
    assert students.count() == 100


def test_create(new_db: DataBase) -> None:
    db = new_db
    assert db.num_tables() == 0
    with pytest.raises(Exception):
        _ = db.get_table('Students')
    create_students_table(db)
    assert db.num_tables() == 1
    assert db.get_tables_names() == ['Students']
    students = db.get_table('Students')
    add_student(students, 111, Birthday=dt.datetime(1995, 4, 28))
    assert students.count() == 1
    students.delete_record(1_000_111)
    assert students.count() == 0
    with pytest.raises(ValueError):
        students.delete_record(key=1_000_111)

    db1 = DataBase()
    assert db1.num_tables() == 1
    db1.delete_table('Students')
    assert db1.num_tables() == 0


def test_update(new_db: DataBase) -> None:
    students = create_students_table(new_db)
    add_student(students, 111, Birthday=dt.datetime(1995, 4, 28))
    assert students.count() == 1
    students.update_record(1_000_111, dict(First='Jane', Last='Doe'))
    assert students.get_record(1_000_111)['First'] == 'Jane'
    with pytest.raises(ValueError):  # record already exists
        add_student(students, 111)


def test_50_students(new_db: DataBase) -> None:
    students = create_students_table(new_db, num_students=50)
    assert students.count() == 50
    students.delete_record(1_000_001)
    students.delete_records([SelectionCriteria('ID', '=', 1_000_020)])
    students.delete_records([SelectionCriteria('ID', '<', 1_000_003)])
    students.delete_records([SelectionCriteria('ID', '>', 1_000_033)])
    students.delete_records([
        SelectionCriteria('ID', '>', 1_000_020),
        SelectionCriteria('ID', '<', 1_000_023)
    ])
    assert students.count() == 28
    students.update_record(1_000_009, dict(First='Jane', Last='Doe'))
    results = students.query_table([SelectionCriteria('First', '=', 'Jane')])
    assert len(results) == 1
    assert results[0]['First'] == 'Jane'


def test_performance(new_db: DataBase) -> None:
    num_records = 200
    assert db_size() == 0
    insert_start = time.time()
    students = create_students_table(new_db, num_records)
    insert_stop = time.time()
    size_100 = db_size()

    assert 0 < size_100 < 1_000_000
    assert insert_stop - insert_start < 20

    delete_start = time.time()
    for i in range(num_records):
        students.delete_records([SelectionCriteria('ID', '=', 1_000_000 + i)])
    delete_stop = time.time()
    assert delete_stop - delete_start < 20


def test_bad_key(new_db: DataBase) -> None:
    with pytest.raises(ValueError):
        _ = new_db.create_table('Students', STUDENT_FIELDS, 'BAD_KEY')


