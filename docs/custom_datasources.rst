
*******************
Custom Data Sources
*******************

To make a custom data source, you need to write your own
:class:`BaseDataSource <datatest.BaseDataSource>` subclass.  You can
download :download:`template.py <_static/template.py>` to use as a
starting point (includes basic methods and unit tests).


How To
======


Class Template
--------------

::

    import datatest

    class MyDataSource(datatest.BaseDataSource):
        def __init__(self):
            """Initialize self."""
            return NotImplemented

        def __repr__(self):
            """Return a string representation of the data source."""
            return NotImplemented

        def columns(self):
            """Return a sequence (e.g. a list) of column names."""
            return NotImplemented

        def slow_iter(self):
            """Return iterable of dict rows (like csv.DictReader)."""
            return NotImplemented

        #def sum(column, **filter_by):
        #    """Return sum of values in column."""

        #def count(column, **filter_by):
        #    """Return count of non-empty values in column."""

        #def unique(*column, **filter_by)
        #    """Return iterable of tuples of unique column values."""


