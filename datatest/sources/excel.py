from __future__ import absolute_import
from .base import BaseSource
from .sqlite import SqliteSource


class ExcelSource(BaseSource):
    """Loads first worksheet from XLSX or XLS file *path*::

        subjectData = datatest.ExcelSource('mydata.xlsx')

    Specific worksheets can be accessed by name::

        subjectData = datatest.ExcelSource('mydata.xlsx', 'Sheet 2')
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

        # Build iterable for worksheet.
        iterrows = (sheet.row(i) for i in range(sheet.nrows))
        iterrows = ([x.value for x in row] for row in iterrows)

        # Build source from records, release resources.
        columns = next(iterrows)
        self._source = SqliteSource.from_records(iterrows, columns)
        book.release_resources()

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_file = self._file_repr
        return '{0}({1})'.format(cls_name, src_file)

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        return iter(self._source)

    def columns(self):
        """Return list of column names."""
        return self._source.columns()

    def sum(self, column, group_by=None, **filter_by):
        return self._source.sum(column, group_by, **filter_by)

    def count(self, group_by=None, **filter_by):
        return self._source.count(group_by, **filter_by)

    def aggregate(self, function, column, group_by=None, **filter_by):
        return self._source.aggregate(function, column, group_by, **filter_by)

    def distinct(self, column, **filter_by):
        return self._source.distinct(column, **filter_by)
