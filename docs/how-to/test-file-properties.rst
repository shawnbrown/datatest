
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
                pattern = r'../*.*'
                paths = (p for p in pathlib.Path('.').glob(pattern) if p.is_file())
                properties_dict = (get_properties(p) for p in paths)
                df = pd.DataFrame.from_records(properties_dict)
                df.set_index(['path'], inplace=True)
                return df


            def test_filetype(df):
                def csv_or_txt(x):  # <- Helper function.
                    suffix = pathlib.Path(x).suffix
                    return suffix.lower() in {'.csv', '.txt'}

                msg = 'Must be CSV or TXT files.'
                dt.validate(df.index, csv_or_txt, msg=msg)


            def test_filename(df):
                msg = 'Must be lowercase with no spaces.',
                dt.validate.regex(df['name'], r'[a-z0-9_.\-]+', msg=msg)


            def test_freshness(df):
                one_week_ago = datetime.date.today() - datetime.timedelta(days=-7)
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
                pattern = r'../*.*'
                paths = (p for p in pathlib.Path('.').glob(pattern) if p.is_file())
                dict_of_lists = collections.defaultdict(list)
                for path in paths:
                    properties_dict = get_properties(path)
                    for k, v in properties_dict.items():
                        dict_of_lists[k].append(v)
                return dict_of_lists


            def test_filetype(files_info):
                def csv_or_txt(x):  # <- Helper function.
                    suffix = pathlib.Path(x).suffix
                    return suffix.lower() in {'.csv', '.txt'}

                msg = 'Must be CSV or TXT files.'
                validate(files_info['path'], csv_or_txt, msg=msg)


            def test_filename(files_info):
                msg = 'Must be lowercase with no spaces.',
                validate.regex(files_info['name'], r'[a-z0-9_.\-]+', msg=msg)


            def test_freshness(files_info):
                data = dict(zip(files_info['path'], files_info['modified_date']))

                one_week_ago = datetime.date.today() - datetime.timedelta(days=-7)

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

    import datetime
    import os

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
