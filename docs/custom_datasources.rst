
Custom Data Sources
===================

!!! TODO !!!


Minimal Class
---------------
::

    import datatest

    class MyDataSource(datatest.BaseDataSource):
        def __init__(self):
            """Initialize self."""
            return NotImplemented

        def __str__(self):
            """Return a brief description of the data source."""
            return NotImplemented

        def slow_iter(self):
            """Return iterable of dict rows (like csv.DictReader)."""
            return NotImplemented

        def columns(self):
            """Return a sequence (or collection) of column names."""
            return NotImplemented

