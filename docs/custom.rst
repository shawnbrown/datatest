
Custom Sources
==============

:mod:`datatest` is designed to work with tabular data stored in spreadsheet
files or database tables but it's also possible to create custom data sources
for other formats.

If you need to test data in a format that's not currently supported,
you can make your own custom data source.  You do this by subclassing
:class:`BaseSource` and implementing the basic, common methods.

As a starting point you can use this :download:`template.py
<_static/template.py>` file to write and test your custom data source.

.. autoclass:: datatest.BaseSource
    :members: __init__, __repr__, __iter__, columns, distinct, sum, count, reduce
