# -*- coding: utf-8 -*-
from __future__ import absolute_import
from ..dataaccess.sqltemp import TemporarySqliteTable
from datatest import SqliteBase


class ExcelSource(SqliteBase):
    """Loads first worksheet from XLSX or XLS file *path*::

        subject = datatest.ExcelSource('mydata.xlsx')

    Specific worksheets can be accessed by name::

        subject = datatest.ExcelSource('mydata.xlsx', 'Sheet 2')

    .. note::
        This data source is optional---it requires the third-party
        library `xlrd <https://pypi.python.org/pypi/xlrd>`_.
    """
    def __init__(self, path, worksheet=None, in_memory=False):
        """Initialize self."""
        try:
            import xlrd
        except ImportError:
            raise ImportError(
                "No module named 'xlrd'\n"
                "\n"
                "This is an optional data source that requires the "
                "third-party library 'xlrd'."
            )

        self._file_repr = repr(path)

        # Open Excel file and get worksheet.
        book = xlrd.open_workbook(path, on_demand=True)
        if worksheet:
            sheet = book.sheet_by_name(worksheet)
        else:
            sheet = book.sheet_by_index(0)

        # Build SQLite table from records, release resources.
        iterrows = (sheet.row(i) for i in range(sheet.nrows))
        iterrows = ([x.value for x in row] for row in iterrows)
        columns = next(iterrows)  # <- Get header row.
        temptable = TemporarySqliteTable(iterrows, columns)
        book.release_resources()

        # Calling super() with older convention to support Python 2.7 & 2.6.
        super(ExcelSource, self).__init__(temptable.connection, temptable.name)
