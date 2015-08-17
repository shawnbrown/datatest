
from datatest.datasource import BaseDataSource
from datatest.datasource import SqliteDataSource


try:
    import xlrd
except ImportError:
    xlrd = None


class ExcelDataSource(BaseDataSource):
    """Loads XLSX or XLS *worksheet* from file *path*::

        subjectData = datatest.ExcelDataSource('mydata.xlsx', 'Sheet 2')

    If *worksheet* is not specified, defaults to the the first worksheet::

        subjectData = datatest.ExcelDataSource('mydata.xlsx')

    """
    def __init__(self, path, worksheet=None, in_memory=False):
        """Initialize self."""
        self._file_repr = repr(path)

        if not xlrd:
            raise ImportError("No module named 'xlrd'\n\n"
                              "This is an optional data source that "
                              "requires the third-party library 'xlrd'.")

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
        self._source = SqliteDataSource.from_records(iterrows, columns)
        book.release_resources()

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_file = self._file_repr
        return '{0}({1})'.format(cls_name, src_file)

    def columns(self):
        """Return list of column names."""
        return self._source.columns()

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        return self._source.slow_iter()

    def sum(self, column, **filter_by):
        """Return sum of values in column."""
        return self._source.sum(column, **filter_by)

    def count(self, **filter_by):
        """Return count of rows."""
        return self._source.count(**filter_by)

    def unique(self, *column, **filter_by):
        """Return iterable of tuples of unique column values."""
        return self._source.unique(*column, **filter_by)

    def set(self, column, **filter_by):
        """Convenience function for unwrapping single column results
        from ``unique()`` and returning as a set."""
        return self._source.set(column, **filter_by)

