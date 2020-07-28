import json
from typing import List
import operator as op

import db_api


def check(record, criteria: List[db_api.SelectionCriteria]):
    ops = {'>': op.gt, '<': op.lt, '=': op.eq}
    for c in criteria:
        if record.get(c.field_name) is None:
            return False
        if not ops[c.operator](record[c.field_name], c.value):
            return False
    return True


def add(d, data_key, file_num):
    if d.get(data_key):
        d[data_key].append(file_num)
    else:
        d[data_key] = [file_num]


def search_index(path, key):
    with open(path) as index_file:
        index = json.load(index_file)

    if index.get(str(key)) is None:
        raise ValueError()
    return index[str(key)]
