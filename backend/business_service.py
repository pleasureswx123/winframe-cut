"""业务层级存取：查询和修改始终限定所属用户。"""
import json
from uuid import uuid4
from fastapi import HTTPException
from .auth import now
from .database import connect
from .geometry import calculate

TABLES = {'customers', 'houses', 'windows'}
JSON_FIELDS = {'stocks', 'settings', 'glass_groups', 'payload'}


def dump(value):
    return json.dumps(value, ensure_ascii=False)


def serialize(row):
    result = dict(row)
    for key in ('custom_profiles', 'custom_glass'):
        if key in result:result[key] = bool(result[key])
    for key in JSON_FIELDS & result.keys():
        result[key] = json.loads(result[key])
    if 'payload' in result:
        result['project'] = result.pop('payload')
    return result


def owned(db, table, object_id, owner_id):
    if table not in TABLES:
        raise ValueError('未知业务表')
    row = db.execute(f'SELECT * FROM {table} WHERE id=? AND owner_id=?', (object_id, owner_id)).fetchone()
    if row is None:
        raise HTTPException(404, '数据不存在')
    return row


def get_record(table, object_id, owner_id):
    with connect() as db:
        return serialize(owned(db, table, object_id, owner_id))


def list_records(table, owner_id, page=1, page_size=20, q='', parent_id=None):
    if table not in TABLES:
        raise ValueError('未知业务表')
    where, args = 'owner_id=?', [owner_id]
    if q:
        where += " AND name LIKE ? ESCAPE '\\'"
        args.append('%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%')
    if parent_id:
        parent_key = 'customer_id' if table == 'houses' else 'house_id'
        where += f' AND {parent_key}=?'
        args.append(parent_id)
    with connect() as db:
        total = db.execute(f'SELECT COUNT(*) FROM {table} WHERE {where}', args).fetchone()[0]
        rows = db.execute(f'SELECT * FROM {table} WHERE {where} ORDER BY updated DESC,id LIMIT ? OFFSET ?',
                          [*args, page_size, (page - 1) * page_size]).fetchall()
    return {'items': [serialize(r) for r in rows], 'total': total, 'page': page, 'page_size': page_size}


def save_record(table, data, owner_id, object_id=None):
    if table not in TABLES:
        raise ValueError('未知业务表')
    values = data.model_dump()
    if table == 'windows':
        calculate(data.project)
        values['name'] = data.project.name
        values['payload'] = values.pop('project')
    values['updated'] = now()
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if object_id:
            owned(db, table, object_id, owner_id)
            if table == 'houses':
                for key in ('custom_profiles','custom_glass'):
                    if key not in data.model_fields_set:values.pop(key,None)
        if table == 'houses':
            owned(db, 'customers', values['customer_id'], owner_id)
        if table == 'windows':
            owned(db, 'houses', values['house_id'], owner_id)
        for key in JSON_FIELDS & values.keys():
            values[key] = dump(values[key])
        if object_id:
            assignments = ','.join(f'{key}=?' for key in values)
            db.execute(f'UPDATE {table} SET {assignments} WHERE id=? AND owner_id=?', [*values.values(), object_id, owner_id])
        else:
            object_id = uuid4().hex
            values.update(id=object_id, owner_id=owner_id)
            if table != 'windows':
                values['created'] = values['updated']
            columns = ','.join(values)
            placeholders = ','.join('?' for _ in values)
            db.execute(f'INSERT INTO {table} ({columns}) VALUES ({placeholders})', list(values.values()))
        return serialize(owned(db, table, object_id, owner_id))


def delete_record(table, object_id, owner_id):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        owned(db, table, object_id, owner_id)
        if table != 'windows':
            child, key = ('houses', 'customer_id') if table == 'customers' else ('windows', 'house_id')
            if db.execute(f'SELECT 1 FROM {child} WHERE {key}=? LIMIT 1', (object_id,)).fetchone():
                raise HTTPException(409, '仍有下级数据，请先处理后再删除')
        db.execute(f'DELETE FROM {table} WHERE id=? AND owner_id=?', (object_id, owner_id))
    return {'ok': True}
