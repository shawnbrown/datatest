

.. module:: datatest

.. meta::
    :description: How to handle relative file paths when testing.
    :keywords: testing, relative, paths, fixture


##############################
How to Use Relative File Paths
##############################

In Python, file paths are relative to your *current working directory*.
By default, this is the directory you were in when you ran your script.

Our example will use the following directory structure:

.. code-block:: none

    myproject/
    ├── tests/
    │   └── test_mydata.py
    └── mydata.csv

The **test_mydata.py** script needs to access data in the **mydata.csv**
file. If we navigate to the **myproject/tests/** folder and run our
script, we need to use the path ``'../mydata.csv'``. But if we are one
level up in the directory structure, we would need to use ``'mydata.csv'``
instead.

To handle this issue, we can use datatest's :class:`working_directory`
support to reliably use relative file references:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 8

            import pytest
            from datatest import working_directory
            from datatest import Select

            ...

            @pytest.fixture(scope='module')
            @working_directory(__file__)
            def mydata():
                return Select('../mydata.csv')

            ...

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 8

            from datatest import working_directory
            from datatest import Select

            ...

            def setUpModule():
                global mydata
                with working_directory(__file__):
                    users = Select('../mydata.csv')

            ...

The above example temporarily sets the working directory relative
to the script itself (using the special ``__file__`` variable). And
once the fixture is loaded, the working directory reverts back to
its original value. This allows us to call our script from any
directory and the relative file path will still work as desired.
