
from datatest.datasource import BaseDataSource
from datatest.datasource import SqliteDataSource


try:
    import xlrd
except ImportError:
    xlrd = None

try:
    import pandas
except ImportError:
    pandas = None


class ExcelDataSource(BaseDataSource):
    """Loads first worksheet from XLSX or XLS file *path*::

        subjectData = datatest.ExcelDataSource('mydata.xlsx')

    Specific worksheets can be accessed by name::

        subjectData = datatest.ExcelDataSource('mydata.xlsx', 'Sheet 2')

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


class PandasDataSource(BaseDataSource):
    """Loads pandas DataFrame:
    ::
        subjectData = datatest.PandasDataSource(df)

    """
    def __init__(self, df):
        """Initialize self."""
        self._df = df
        self._default_index = (df.index.names == [None])

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        hex_id = hex(id(self._df))
        return "{0}(<pandas.DataFrame object at {1}>)".format(cls_name, hex_id)

    def columns(self):
        """Return list of column names."""
        if self._default_index:
            return list(self._df.columns)
        return list(self._df.index.names) + list(self._df.columns)

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        columns = self.columns()
        if self._default_index:
            for row in self._df.itertuples(index=not self._default_index):
                yield dict(zip(columns, row))
        else:
            gettup = lambda x: x if isinstance(x, tuple) else tuple([x])
            addtup = lambda x: gettup(x[0]) + gettup(x[1:])
            for row in self._df.itertuples(index=not self._default_index):
                yield dict(zip(columns, addtup(row)))

    def unique(self, *column, **filter_by):
        """Return iterable of unique tuples of column values."""
        df = self._filter_by(self._df, self._default_index, **filter_by)
        df = df[list(column)].drop_duplicates()
        for row in df.itertuples(index=False):
            yield row

    def sum(self, column, **filter_by):
        """Return sum of values in column."""
        df = self._filter_by(self._df, self._default_index, **filter_by)
        s = df[column].replace('', pandas.np.nan)
        return s.astype(pandas.np.float).sum()

    def count(self, **filter_by):
        """Return count of rows."""
        df = self._filter_by(self._df, self._default_index, **filter_by)
        return len(df)

    @staticmethod
    def _filter_by(df, default_index, **filter_by):
        """Filter iterable by keywords (column=value, etc.)."""
        if not default_index:
            df = df.reset_index()

        for col, val in filter_by.items():
            if isinstance(val, (list, tuple)):
                df = df[df[col].isin(val)]
            else:
                df = df[df[col] == val]
        return df

    @classmethod
    def from_source(cls, source):
        """Alternate constructor to load an existing data source:
        ::

            subjectData = datatest.PandasDataSource.from_source(source)

        """
        return cls.from_records(source.slow_iter(), source.columns())

    @classmethod
    def from_records(cls, data, columns):
        """Alternate constructor to load an existing collection of
        records.  Loads *data* (an iterable of lists, tuples, or dicts)
        as a DataFrame with the given *columns*::

            subjectData = datatest.PandasDataSource.from_records(records, columns)

        """
        df = pandas.DataFrame(data, columns=columns)
        return cls(df)
