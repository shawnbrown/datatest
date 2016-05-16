
Custom Sources
==============

:mod:`datatest` is designed to work with tabular data stored in spreadsheet
files or database tables but it's also possible to create custom data sources
for other formats.

If you need to test data in a format that's not currently supported,
you can make your own custom data source.  You do this by subclassing
:class:`BaseSource` and implementing the basic, common methods.

.. todo::
    Make an updated template file.  The original :download:`template.py
    <_static/template.py>` is extremely out of date and doesn't match
    the current data source API.

.. todo:: Give examples of BaseSource and SqliteBase subclasses.
