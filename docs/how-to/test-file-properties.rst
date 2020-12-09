
.. currentmodule:: datatest

.. meta::
    :description: How to test file properties.
    :keywords: datatest, test file properties


###########################
How to Test File Properties
###########################

In some cases, you might need to check the properties of several
files at once. This can be accomplished by loading the properties
into a DataFrame or other object using a fixture.


Example
=======

.. tabs::

    .. group-tab:: Pandas

        .. code-block:: python
            :linenos:

            import datetime
            import os
            import pathlib
            import pytest
            import pandas as pd
            import datatest as dt


            def get_properties(file_path):
                """Accepts a pathlib.Path and returns a dict of file properties."""
                stats = file_path.stat()

                size_in_mb = stats.st_size / 1024 / 1024  # Convert bytes to megabytes.

                return {
                    'path': str(file_path),
                    'name': file_path.name,
                    'modified_date': datetime.date.fromtimestamp(stats.st_mtime),
                    'size': round(size_in_mb, 2),
                    'readable': os.access(file_path, os.R_OK),
                    'writable': os.access(file_path, os.W_OK),
                }


            @pytest.fixture(scope='session')
            @dt.working_directory(__file__)
            def df():
                directory = '.'  # Current directory.
                pattern = '*.csv'  # Matches CSV files.
                paths = (p for p in pathlib.Path(directory).glob(pattern) if p.is_file())
                dict_records = (get_properties(p) for p in paths)
                df = pd.DataFrame.from_records(dict_records)
                df = df.set_index(['path'])
                return df


            def test_filename(df):
                def is_lower_case(x):  # <- Helper function.
                    return x.islower()

                msg = 'Must be lowercase.'
                dt.validate(df['name'], is_lower_case, msg=msg)


            def test_freshness(df):
                one_week_ago = datetime.date.today() - datetime.timedelta(days=7)
                msg = 'Must be no older than one week.'
                dt.validate.interval(df['modified_date'], min=one_week_ago, msg=msg)


            def test_filesize(df):
                msg = 'Must be 1 MB or less in size.'
                dt.validate.interval(df['size'], max=1.0, msg=msg)


            def test_permissions(df):
                msg = 'Must have read and write permissions.'
                dt.validate(df[['readable', 'writable']], (True, True), msg=msg)


            if __name__ == '__main__':
                import sys
                sys.exit(pytest.main(sys.argv))


    .. group-tab:: dict-of-lists

        .. code-block:: python
            :linenos:

            import datetime
            import os
            import pathlib
            import pytest
            import collections
            from datatest import validate, working_directory


            def get_properties(file_path):
                """Accepts a pathlib.Path and returns a dict of file properties."""
                stats = file_path.stat()

                size_in_mb = stats.st_size / 1024 / 1024  # Convert bytes to megabytes.

                return {
                    'path': str(file_path),
                    'name': file_path.name,
                    'modified_date': datetime.date.fromtimestamp(stats.st_mtime),
                    'size': round(size_in_mb, 2),
                    'readable': os.access(file_path, os.R_OK),
                    'writable': os.access(file_path, os.W_OK),
                }


            @pytest.fixture(scope='session')
            @working_directory(__file__)
            def files_info():
                directory = '.'  # Current directory.
                pattern = '*.csv'  # Matches CSV files.
                paths = (p for p in pathlib.Path(directory).glob(pattern) if p.is_file())
                dict_of_lists = collections.defaultdict(list)
                for path in paths:
                    properties_dict = get_properties(path)
                    for k, v in properties_dict.items():
                        dict_of_lists[k].append(v)
                return dict_of_lists


            def test_filename(files_info):
                def is_lower_case(x):  # <- Helper function.
                    return x.islower()

                msg = 'Must be lowercase.'
                validate(files_info['name'], is_lower_case, msg=msg)


            def test_freshness(files_info):
                data = dict(zip(files_info['path'], files_info['modified_date']))

                one_week_ago = datetime.date.today() - datetime.timedelta(days=7)

                msg = 'Must be no older than one week.'
                validate.interval(data, min=one_week_ago, msg=msg)


            def test_filesize(files_info):
                data = dict(zip(files_info['path'], files_info['size']))

                msg = 'Must be 1 MB or less in size.'
                validate.interval(data, max=1.0, msg=msg)


            def test_permissions(files_info):
                values = zip(files_info['readable'], files_info['writable'])
                data = dict(zip(files_info['path'], values))

                msg = 'Must have read and write permissions.'
                validate(data, (True, True), msg=msg)


            if __name__ == '__main__':
                import sys
                sys.exit(pytest.main(sys.argv))


Other Properties
================

To check other file properties, you can modify or add to the
``get_properties()`` function.

Below, we count the number of lines in each file and add a
``line_count`` to the dictionary of properties:

.. code-block:: python
    :emphasize-lines: 12-13,22
    :linenos:

    import datetime
    import os

    ...

.. code-block:: python
    :emphasize-lines: 9-10,19
    :linenos:
    :lineno-start: 7

    ...

    def get_properties(file_path):
        """Accepts a pathlib.Path and returns a dict of file properties."""
        stats = file_path.stat()

        size_in_mb = stats.st_size / 1024 / 1024  # Convert bytes to megabytes.

        with open(file_path) as fh:
            line_count = len(fh.readlines())

        return {
            'path': str(file_path),
            'name': file_path.name,
            'modified_date': datetime.date.fromtimestamp(stats.st_mtime),
            'size': round(size_in_mb, 2),
            'readable': os.access(file_path, os.R_OK),
            'writable': os.access(file_path, os.W_OK),
            'line_count': line_count,
        }

    ...


See Also
========

* :doc:`file-names`
* :doc:`date-time-obj`
