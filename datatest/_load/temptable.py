# -*- coding: utf-8 -*-
import sqlite3
from collections import Iterable
from collections import Mapping
from itertools import count
from itertools import chain


try:
    string_types = basestring
except NameError:
    string_types = str


def table_exists(cursor, table):
    cursor.execute('''
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?

        UNION

        SELECT name
        FROM sqlite_temp_master
        WHERE type='table' AND name=?
    ''', (table, table))
    return bool(cursor.fetchall())


_table_names = ('tbl{0}'.format(x) for x in count())
def new_table_name(cursor):
    global _table_names

    new_name = next(_table_names)
    while table_exists(cursor, new_name):
        new_name = next(_table_names)

    return new_name


def normalize_names(names):
    def normalize(name):
        name = str(name).strip()  # Strip whitespace.
        return '"{0}"'.format(name.replace('"', '""'))  # Escape quotes.

    if isinstance(names, string_types) or not isinstance(names, Iterable):
        return normalize(names)
    return [normalize(name) for name in names]


def create_table(cursor, table, columns, default="''"):
    """Creates a temporary table using *table* and *columns* names."""
    columns = normalize_names(columns)
    if columns.count('""') > 1:
        custom_message = ('duplicate column name: contains multiple '
                          'columns where names are empty strings or '
                          'whitespace')
        raise sqlite3.OperationalError(custom_message)
        # Above: The default language for this corner case is very
        # confusing. Catching this condition and raising the error
        # before execution is simpler than parsing the inevitable
        # OperationalError and re-raising it with a modified message.

    if not default:
        default = 'NULL'
    column_defs = ['{0} DEFAULT {1}'.format(x, default) for x in columns]
    column_defs = ', '.join(column_defs)

    statement = 'CREATE TEMPORARY TABLE {0} ({1})'.format(table, column_defs)
    cursor.execute(statement)


def get_columns(cursor, table):
    """Returns list of column names used in table."""
    cursor.execute('PRAGMA table_info({0})'.format(table))
    columns = [x[1] for x in cursor]
    if not columns:
        raise sqlite3.ProgrammingError('no such table: {0}'.format(table))
    return columns


def insert_records(cursor, table, columns, records):
    table = normalize_names(table)
    columns = normalize_names(columns)
    sql = 'INSERT INTO {0} ({1}) VALUES ({2})'.format(
        table,
        ', '.join(columns),
        ', '.join(['?'] * len(columns)),
    )
    try:
        cursor.executemany(sql, records)
    except sqlite3.ProgrammingError as error:
        if 'incorrect number of bindings' in str(error).lower():
            msg = (
                '{0}\n\nThe records {1!r} contains some rows with too '
                'few or too many values. Before loading this data, it '
                'must be normalized so each row contains a number of '
                'values equal to the number of columns being loaded.'
            ).format(error, records)
            error = sqlite3.ProgrammingError(msg)
            error.__cause__ = None
        raise error


def alter_table(cursor, table, columns, default="''"):
    existing_columns = set(normalize_names(get_columns(cursor, table)))
    for column in normalize_names(columns):
        if column in existing_columns:
            continue

        if not default:
            default = 'NULL'
        sql = 'ALTER TABLE {0} ADD COLUMN {1} DEFAULT {2}'
        sql = sql.format(table, column, default)

        cursor.execute(sql)
        existing_columns.add(column)


def drop_table(cursor, table):
    table = normalize_names(table)
    cursor.execute('DROP TABLE IF EXISTS {0}'.format(table))


_savepoint_names = ('svpnt{0}'.format(x) for x in count())
class savepoint(object):
    """Sqlite SAVEPOINT context manager."""
    def __init__(self, cursor):
        global _savepoint_names

        if cursor.connection.isolation_level is not None:
            msg = ('The cursor\'s connection must be running in '
                   '"autocommit" mode for precise transaction and '
                   'savepoint handling. Turn on autocommit by '
                   'assigning "isolation_level=None".')
            raise ValueError(msg)

        self.name = next(_savepoint_names)
        self.cursor = cursor

    def __enter__(self):
        self.cursor.execute('SAVEPOINT {0}'.format(self.name))

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.cursor.execute('RELEASE {0}'.format(self.name))
        else:
            self.cursor.execute('ROLLBACK TO {0}'.format(self.name))


def load_data(cursor, table, *args):
    """
    load_data(cursor, table, columns, records)
    load_data(cursor, table, records)
    """
    try:
        records, = args
        columns = None
    except ValueError:
        columns, records = args

    records = iter(records)
    first_record = next(records, None)
    if columns:
        if first_record:
            records = chain([first_record], records)
    else:
        if not first_record:
            return  # <- EXIT! (No table created.)
        try:  # Try mapping.
            columns = list(first_record.keys())
            records = chain([first_record], records)
        except AttributeError:
            try:  # Try namedtuple.
                columns = first_record._fields
                records = chain([first_record], records)
            except AttributeError:
                columns = first_record  # Use first row as column names.

    if not isinstance(columns, Iterable) or isinstance(columns, str):
        msg = 'expected iterable of strings, got {0!r}'
        raise TypeError(msg.format(columns))
    columns = list(columns)  # Make sure columns is a sequence.

    if isinstance(first_record, Mapping):
        records = ([rec.get(c, '') for c in columns] for rec in records)

    with savepoint(cursor):
        if table_exists(cursor, table):
            alter_table(cursor, table, columns, default="''")
        else:
            create_table(cursor, table, columns, default="''")
        insert_records(cursor, table, columns, records)
