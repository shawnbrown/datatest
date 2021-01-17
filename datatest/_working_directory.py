"""working_directory context manager."""

import os
from ._compatibility import contextlib


class working_directory(contextlib.ContextDecorator):
    """A context manager to temporarily set the working directory
    to a given *path*. If *path* specifies a file, the file's
    directory is used. When exiting the with-block, the working
    directory is automatically changed back to its previous
    location.

    You can use Python's :py:obj:`__file__` constant to load data
    relative to a file's current directory:

    .. code-block:: python
        :emphasize-lines: 4

        from datatest import working_directory
        import pandas as pd

        with working_directory(__file__):
            my_df = pd.read_csv('myfile.csv')

    This context manager can also be used as a decorator:

    .. code-block:: python
        :emphasize-lines: 4

        from datatest import working_directory
        import pandas as pd

        @working_directory(__file__)
        def my_df():
            return pd.read_csv('myfile.csv')

    In some cases, you may want to forgo the use of a context manager
    or decorator. You can explicitly control directory switching with
    the ``change()`` and ``revert()`` methods:

    .. code-block:: python
        :emphasize-lines: 4,8

        from datatest import working_directory

        work_dir = working_directory(__file__)
        work_dir.change()

        ...

        work_dir.revert()
    """
    def __init__(self, path):
        if os.path.isfile(path):
            path = os.path.dirname(path)
        self._working_dir = os.path.abspath(path)
        self._original_dir = None  # Assigned on __enter__(), not before.

    def __enter__(self):
        if self._original_dir:
            msg = 'cannot reenter {0}, already entered from {1!r}'.format(
                self.__class__.__name__,
                self._original_dir,
            )
            raise RuntimeError(msg)

        self._original_dir = os.path.abspath(os.getcwd())
        os.chdir(self._working_dir)

    def __exit__(self, exc_type, exc_value, traceback):
        if self._original_dir:
            os.chdir(self._original_dir)
            self._original_dir = None

    def change(self):
        """Change to the defined working directory (enter the context).

        While operating in a working directory context, you cannot
        enter it again. Calling ``change()`` a second time will raise
        a :py:class:`RuntimeError`---you must first call ``revert()``.
        """
        self.__enter__()

    def revert(self):
        """Revert to the original working directory (exit the context).

        If no context has been entered, calling ``revert()`` will do
        nothing and pass without error.
        """
        self.__exit__(None, None, None)
