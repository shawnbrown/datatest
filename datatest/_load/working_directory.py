# -*- coding: utf-8 -*-
import os
from .._compatibility import contextlib


class working_directory(contextlib.ContextDecorator):
    """A context manager to temporarily set the working directory
    to a given *path*. If *path* specifies a file, the file's
    directory is used. When exiting the with-block, the working
    directory is automatically changed back to its previous
    location.

    Use the global ``__file__`` variable to load data relative to
    test file's current directory::

        with datatest.working_directory(__file__):
            select = datatest.Selector('myfile.csv')

    This context manager can also be used as a decorator::

        @datatest.working_directory(__file__)
        def myfile():
            return datatest.Selector('myfile.csv')
    """
    def __init__(self, path):
        if os.path.isfile(path):
            path = os.path.dirname(path)
        self._working_dir = os.path.abspath(path)

    def __enter__(self):
        self._original_dir = os.path.abspath(os.getcwd())
        os.chdir(self._working_dir)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self._original_dir)
