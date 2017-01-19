# -*- coding: utf-8 -*-
import inspect
import os
import sys
import warnings

from ..utils.builtins import *
from ..dataaccess.csvreader import UnicodeCsvReader
from ..dataaccess.sqltemp import TemporarySqliteTable

from .sqlite import SqliteBase


class CsvSource(SqliteBase):
    """Loads CSV data from *file* (path or file-like object):
    ::

        subject = datatest.CsvSource('mydata.csv')
    """
    def __init__(self, file, encoding=None, in_memory=False, **fmtparams):
        """Initialize self."""
        self._file_repr = repr(file)

        # If *file* is relative path, uses directory of calling file as base.
        if isinstance(file, str) and not os.path.isabs(file):
            calling_frame = sys._getframe(1)
            calling_file = inspect.getfile(calling_frame)
            base_path = os.path.dirname(calling_file)
            file = os.path.join(base_path, file)
            file = os.path.normpath(file)

        # Create temporary SQLite table object.
        if encoding:
            with UnicodeCsvReader(file, encoding=encoding, **fmtparams) as reader:
                columns = next(reader)  # Header row.
                temptable = TemporarySqliteTable(reader, columns)
        else:
            try:
                with UnicodeCsvReader(file, encoding='utf-8', **fmtparams) as reader:
                    columns = next(reader)  # Header row.
                    temptable = TemporarySqliteTable(reader, columns)

            except UnicodeDecodeError:
                with UnicodeCsvReader(file, encoding='iso8859-1', **fmtparams) as reader:
                    columns = next(reader)  # Header row.
                    temptable = TemporarySqliteTable(reader, columns)

                # Prepare message and raise as warning.
                try:
                    filename = os.path.basename(file)
                except AttributeError:
                    filename = repr(file)
                msg = ('\nData in file {0!r} does not appear to be encoded '
                       'as UTF-8 (used ISO-8859-1 as fallback). To assure '
                       'correct operation, please specify a text encoding.')
                warnings.warn(msg.format(filename))

        # Calling super() with older convention to support Python 2.7 & 2.6.
        super(CsvSource, self).__init__(temptable.connection, temptable.name)

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_file = self._file_repr
        return '{0}({1})'.format(cls_name, src_file)
