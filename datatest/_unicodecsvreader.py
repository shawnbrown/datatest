# -*- coding: utf-8 -*-
"""Unicode CSV Reader (Python 3 and Python 2 compatible)."""

import csv
import io
import sys


class UnicodeCsvReader:
    """UnicodeCsvReader wraps the standard library's ``csv.reader``
    object to support unicode CSV files in both Python 3 and Python 2.

    Example usage::

        with UnicodeCsvReader('myfile.csv', encoding='utf-8') as reader:
            for row in reader:
                process(row)

    The *csvfile* argument can be a file path (as in the example above)
    or a file-like object.  When passing file objects, Python 3
    requires them to be opened in text-mode ('r') while Python 2
    requires them to be opened in binary-mode ('rb').  UnicodeCsvReader
    manages these differences automatically when given a file path.
    """
    def __init__(self, csvfile, encoding='utf-8', dialect='excel', **fmtparams):
        self.encoding = encoding
        self.dialect = dialect
        self._csvfile = csvfile  # Can be path or file-like object.
        self._fileobj = self._get_file_object(csvfile, self.encoding)
        self._reader = csv.reader(self._fileobj, dialect=self.dialect, **fmtparams)

    @property
    def line_num(self):
        return self._reader.line_num

    def __del__(self):
        # Note: If __init__ fails, _fileobj will not exist.
        if hasattr(self, '_fileobj') and self._fileobj != self._csvfile:
            self._fileobj.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.__del__()

    def __iter__(self):
        return self

    @staticmethod
    def _get_file_object(csvfile, encoding):
        if isinstance(csvfile, str):
            return open(csvfile, 'rt', encoding=encoding, newline='')  # <- EXIT!

        if hasattr(csvfile, 'mode'):
            assert 'b' not in csvfile.mode, "File must be open in text mode ('rt')."
        elif issubclass(csvfile.__class__, io.IOBase):
            assert issubclass(csvfile.__class__, io.TextIOBase), ("Stream object must inherit "
                                                                  "from io.TextIOBase.")
        return csvfile

    def __next__(self):
        return next(self._reader)


########################################################################
# Patch `UnicodeCsvReader` if using Python 2.
########################################################################
if sys.version < '3':
    _py3_UnicodeCsvReader = UnicodeCsvReader
    class UnicodeCsvReader(_py3_UnicodeCsvReader):
        @staticmethod
        def _get_file_object(csvfile, encoding):
            if isinstance(csvfile, str):
                return open(csvfile, 'rb')  # <- EXIT!

            if hasattr(csvfile, 'mode'):
                assert 'b' in csvfile.mode, ("When using Python 2, file must "
                                             "be open in binary mode ('rb').")
            elif issubclass(csvfile.__class__, io.IOBase):
                assert not issubclass(csvfile.__class__, io.TextIOBase), ("When using Python 2, "
                                                                          "must use byte stream "
                                                                          "(not text stream).")
            return csvfile

        def __next__(self):
            row = next(self._reader)
            return [s.decode(self.encoding) for s in row]

        def next(self):
            return self.__next__()
