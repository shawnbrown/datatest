
.. currentmodule:: datatest

.. meta::
    :description: How to check file names.
    :keywords: datatest, check file names


##########################
How to Validate File Names
##########################

Sometimes you need to make sure that files are well organized and conform
to some specific naming scheme. To validate the files names in a directory,
simply pass the names themselves as the *data* argument when calling
:func:`validate`. You then control the method of validation with the
*requirement* you provide.

.. admonition:: pathlib Basics
    :class: note

    While there are multiple ways to get file names stored on disk, examples
    on this page use the Standard Library's :py:mod:`pathlib` module. If you're
    not familiar with pathlib, please review some basics examples before
    continuing:

    .. raw:: html

       <details>
       <summary><a>Basic Examples</a></summary>

    These examples assume the following directory structure:

    .. code-block:: none

        ├── file1.csv
        ├── file2.csv
        ├── file3.xlsx
        └── directory1/
            ├── file4.csv
            └── file5.xlsx


    Import the :py:class:`Path <pathlib.Path>` class:

    .. code-block:: python

        >>> from pathlib import Path


    Get a list of file and directory names from the current directory:

    .. code-block:: python

        >>> [str(p) for p in Path('.').iterdir()]
        ['file1.csv', 'file2.csv', 'file3.xlsx', 'directory1']


    Filter the results to just files, no directories, using an ``if``
    clause:

    .. code-block:: python

        >>> [str(p) for p in Path('.').iterdir() if p.is_file()]
        ['file1.csv', 'file2.csv', 'file3.xlsx']


    Get a list of path names ending in ".csv" from the current directory
    using :py:meth:`glob <pathlib.Path.glob>`-style pattern matching:

    .. code-block:: python

        >>> [str(p) for p in Path('.').glob('*.csv')]
        ['file1.csv', 'file2.csv']


    Get a list of CSV paths from the current directory and all subdirectories:

    .. code-block:: python

        >>> [str(p) for p in Path('.').rglob('*.csv')]  # <- Using "recursive glob".
        ['file1.csv', 'file2.csv', 'directory1/file4.csv']


    Get a list of CSV names from the current directory and all subdirectories
    using ``p.name`` instead of ``str(p)`` (excludes directory name):

    .. code-block:: python

        >>> [p.name for p in Path('.').rglob('*.csv')]  # <- p.name excludes directory
        ['file1.csv', 'file2.csv', 'file4.csv']


    Get a list of file and directory paths from the parent directory
    using the special name ``..``:

    .. code-block:: python

        >>> [str(p) for p in Path('..').iterdir()]
        [ <parent directory names here> ]


    .. raw:: html

       </details>


Lowercase
=========

Check that file names are lowercase:

.. code-block:: python

    from pathlib import Path
    from datatest import validate, working_directory


    with working_directory(__file__):
        file_names = (str(p) for p in Path('.').iterdir() if p.is_file())

    def islower(x):
        return x.islower()

    validate(file_names, islower, msg='should be lowercase')


Lowercase Without Spaces
========================

Check that file names are lowercase and don't use spaces:

.. code-block:: python

    from pathlib import Path
    from datatest import validate, working_directory


    with working_directory(__file__):
        file_names = (str(p) for p in Path('.').iterdir() if p.is_file())

    msg = 'Should be lowercase with no spaces.',
    validate.regex(file_names, r'[a-z0-9_.\-]+', msg=msg)


Not Too Long
============

Check that the file names aren't too long (25 characters or less):

.. code-block:: python

    from pathlib import Path
    from datatest import validate, working_directory


    with working_directory(__file__):
        file_names = (str(p) for p in Path('.').iterdir() if p.is_file())

    def not_too_long(x):
        """Path names should be 25 characters or less."""
        return len(x) <= 25

    validate(file_names, not_too_long)


Check for CSV Type
==================

Check that files are CSVs files:

.. code-block:: python

    from pathlib import Path
    from datatest import validate, working_directory


    with working_directory(__file__):
        file_names = (str(p) for p in Path('.').iterdir() if p.is_file())

    def is_csv(x):
        return x.lower().endswith('.csv')

    validate(file_names, is_csv, msg='should be CSV file')


Multiple Files Types
====================

Check that files are CSV, Excel, or DBF file types:

.. code-block:: python

    from pathlib import Path
    from datatest import validate, working_directory


    with working_directory(__file__):
        file_names = (str(p) for p in Path('.').iterdir() if p.is_file())

    def tabular_formats(x):  # <- Helper function.
        """Should be CSV, Excel, or DBF files."""
        suffix = Path(x).suffix
        return suffix.lower() in {'.csv', '.xlsx', '.xls', '.dbf'}

    validate(file_names, tabular_formats)


Specific Files Exist
====================

Using :meth:`validate.superset`, check that the list of file names
includes a given set of required files:

.. code-block:: python

    from pathlib import Path
    from datatest import validate, working_directory


    with working_directory(__file__):
        file_names = (str(p) for p in Path('.').iterdir() if p.is_file())

    validate.superset(file_names, {'readme.txt', 'license.txt', 'config.ini'})


Includes Date
=============

Check that file names begin with a date in YYYYMMDD format (e.g.,
20201103_data.csv):

.. code-block:: python

    from pathlib import Path
    from datatest import validate, working_directory


    with working_directory(__file__):
        file_names = (p.name for p in Path('.').iterdir() if p.is_file())

    msg = 'Should have date prefix followed by an underscore (YYYYMMDD_).'
    validate.regex(file_names, r'^\d{4}\d{2}\d{2}_.+', msg=msg)


You can change the regex pattern to match another naming scheme of your
choice. See the following examples for ideas:

=======================  ===========================  ===================
description              regex pattern                example
=======================  ===========================  ===================
date prefix              ``^\d{4}-\d{2}-\d{2}_.+``    2020-11-03_data.csv
date prefix (no hyphen)  ``^\d{4}\d{2}\d{2}_.+``      20201103_data.csv
date suffix              ``.+_\d{4}-\d{2}-\d{2}.+$``  data_2020-11-03.csv
date suffix (no hyphen)  ``.+_\d{4}\d{2}\d{2}.+$``    data_20201103.csv
=======================  ===========================  ===================


See Also
========

* :doc:`test-file-properties`
