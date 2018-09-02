
.. module:: datatest

.. meta::
    :description: How to check file names.
    :keywords: datatest, check file names


########################
How to Assert File Names
########################

The following example uses :py:func:`glob() <glob.glob>` to get
a list of file names from a specified location and then uses a
helper function to check that they end with ``'.csv'``.

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python

            from glob import glob
            from datatest import validate, working_directory


            def test_file_names():
                with working_directory(__file__):
                    file_list = glob('myfiles/*')

                def is_csv(value):  # <- Helper function.
                    return value.lower().endswith('.csv')

                if not file_list:
                    raise Exception('no files found')
                validate(file_list, is_csv, 'should be CSV files')


    .. group-tab:: Unittest

        .. code-block:: python

            from glob import glob
            from datatest import DataTestCase, working_directory


            class MyTest(DataTestCase):

                def test_file_names(self):
                    with working_directory(__file__):
                        file_list = glob('myfiles/*')

                    def is_csv(value):  # <- Helper function.
                        return value.lower().endswith('.csv')

                    self.assertGreater(len(file_list), 0, 'no files found')
                    self.assertValid(file_list, is_csv, 'should be CSV files')
