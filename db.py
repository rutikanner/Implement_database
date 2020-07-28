import os
import json
import shutil

from typing import Any, Dict, List

import db_api
from pathlib import Path

import record

DB_ROOT = Path('db_files')


class DBTable(db_api.DBTable):
    def count(self) -> int:
        with open(f"{DB_ROOT}/{self.name}/meta_data.json") as the_file:
            meta_data = json.load(the_file)

        return meta_data["count"]

    def insert_record(self, values: Dict[str, Any]) -> None:
        with open(f"{DB_ROOT}/{self.name}/meta_data.json") as the_file:
            meta_data = json.load(the_file)

        with open(f"{DB_ROOT}/{self.name}/{meta_data['files_num']}.json", "r") as the_file:
            data = json.load(the_file)

        with open(f"{DB_ROOT}/{self.name}/{meta_data['key']}_index.json", "r") as the_file:
            index = json.load(the_file)

        if index.get(str(values[meta_data["key"]])) is not None:
            raise ValueError()

        if len(data.keys()) >= 1000:
            with (DB_ROOT / f"{self.name}/ {meta_data['files_num'] + 1}.json").open() as the_file:
                json.dump({values[meta_data["key"]]: values}, the_file)
            meta_data['files_num'] += 1
        else:
            with open(f"{DB_ROOT}/{self.name}/{meta_data['files_num']}.json", "r") as the_file:
                data = json.load(the_file)
            with open(f"{DB_ROOT}/{self.name}/{meta_data['files_num']}.json", "w") as the_file:
                data[values[meta_data["key"]]] = values
                json.dump(data, the_file)

        record.add(index, values[meta_data["key"]], meta_data['files_num'])
        with open(f"{DB_ROOT}/{self.name}/{meta_data['key']}_index.json", "w") as the_file:
            json.dump(index, the_file)

        meta_data["count"] += 1
        with open(f"{DB_ROOT}/{self.name}/meta_data.json", "w") as the_file:
            json.dump(meta_data, the_file)

    def delete_record(self, key: Any) -> None:
        with open(f"{DB_ROOT}/{self.name}/meta_data.json") as the_file:
            meta_data = json.load(the_file)

        with open(f"{DB_ROOT}/{self.name}/{meta_data['key']}_index.json", "r") as the_file:
            index = json.load(the_file)

        if (index.get(str(key)) is None) or len(index[str(key)]) == 0:
            raise ValueError()

        with open(f"{DB_ROOT}/{self.name}/{index[str(key)][0]}.json", "r") as the_file:
            data = json.load(the_file)

        with open(f"{DB_ROOT}/{self.name}/{index[str(key)]}.json", "w") as the_file:
            data.pop(str(key))
            with open(f"{DB_ROOT}/{self.name}/meta_data.json", "r") as meta_data_file:
                meta_data = json.load(meta_data_file)
                meta_data["count"] -= 1

            with open(f"{DB_ROOT}/{self.name}/meta_data.json", "w") as meta_data_file:
                json.dump(meta_data, meta_data_file)

            json.dump(data, the_file)

        with open(f"{DB_ROOT}/{self.name}/{meta_data['key']}_index.json", "w") as the_file:
            index.pop(str(key))
            json.dump(index, the_file)

    def delete_records(self, criteria: List[db_api.SelectionCriteria]) -> None:
        with open(f"{DB_ROOT}/{self.name}/meta_data.json") as the_file:
            meta_data = json.load(the_file)

        for i in range(1, meta_data['files_num'] + 1):
            with open(f"{DB_ROOT}/{self.name}/{i}.json", "r") as the_file:
                data = json.load(the_file)

            for k in data.keys():
                if record.check(data[k], criteria):
                    self.delete_record(k)

    def update_record(self, key: Any, values: Dict[str, Any]) -> None:
        with open(f"{DB_ROOT}/{self.name}/meta_data.json") as the_file:
            meta_data = json.load(the_file)

        i = record.search_index(f"{DB_ROOT}/{self.name}/{meta_data['key']}_index.json", key)[0]
        with open(f"{DB_ROOT}/{self.name}/{i}.json", "r") as the_file:
            data = json.load(the_file)

        with open(f"{DB_ROOT}/{self.name}/{i}.json", "w") as the_file:
            for k in values.keys():
                data[str(key)][k] = values[k]

            json.dump(data, the_file)

    def get_record(self, key: Any) -> Dict[str, Any]:
        with open(f"{DB_ROOT}/{self.name}/meta_data.json") as the_file:
            meta_data = json.load(the_file)

        i = record.search_index(f"{DB_ROOT}/{self.name}/{meta_data['key']}_index.json", key)[0]
        with open(f"{DB_ROOT}/{self.name}/{i}.json", "r") as the_file:
            data = json.load(the_file)

        return data.get(str(key))

    def query_table(self, criteria: List[db_api.SelectionCriteria]) \
            -> List[Dict[str, Any]]:
        res = {}
        with open(f"{DB_ROOT}/{self.name}/meta_data.json") as the_file:
            meta_data = json.load(the_file)
        for i in range(1, meta_data['files_num'] + 1):
            with open(f"{DB_ROOT}/{self.name}/{i}.json", "r") as the_file:
                data = json.load(the_file)
            for k in data.keys():
                if record.check(data[k], criteria):
                    res[k] = data[k]

        return res

    def create_index(self, field_to_index: str) -> None:
        with open(f"{DB_ROOT}/{self.name}/meta_data.json") as the_file:
            meta_data = json.load(the_file)

        with open(f"{DB_ROOT}/{self.name}/{field_to_index}_index.json", "w") as index_file:
            index = {}
            for i in range(1, meta_data['files_num'] + 1):
                with open(f"{DB_ROOT}/{self.name}/{i}.json", "r") as the_file:
                    data = json.load(the_file)
                for k in data.keys():
                    record.add(index, data[k][field_to_index], i)
            json.dump(index, index_file)


class DataBase(db_api.DataBase):
    def create_table(self,
                     table_name: str,
                     fields: List[db_api.DBField],
                     key_field_name: str) -> DBTable:

        li = [f.name for f in fields]
        if key_field_name not in li:
            raise ValueError()
        os.mkdir(f"./{DB_ROOT}/{table_name}")

        with (DB_ROOT / f"{table_name}/meta_data.json").open("w") as the_file:
            json.dump({"must": li, "key": key_field_name, "count": 0, "files_num": 1}, the_file)

        with open(f"{DB_ROOT}/{table_name}/1.json", "w") as the_file:
            json.dump({}, the_file)

        table = DBTable(table_name, fields, key_field_name)
        table.create_index(key_field_name)
        return table

    def num_tables(self) -> int:
        return len(os.listdir(DB_ROOT))

    def get_table(self, table_name: str) -> DBTable:
        with open(f"{DB_ROOT}/{table_name}/meta_data.json") as the_file:
            meta_data = json.load(the_file)

        fields = [db_api.DBField(name, str) for name in meta_data["must"]]

        return DBTable(table_name, fields, meta_data["key"])

    def delete_table(self, table_name: str) -> None:
        shutil.rmtree(f"{DB_ROOT}/{table_name}", ignore_errors=True)

    def get_tables_names(self):
        f = []
        for (dir_path, dir_names, file_names) in os.walk(f"./{DB_ROOT}"):
            f.extend(dir_names)
            break

        return f


