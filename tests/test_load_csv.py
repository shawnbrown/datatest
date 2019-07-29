# -*- coding: utf-8 -*-
import os
import sqlite3
import sys
import warnings
from . import _io as io
from . import _unittest as unittest
from datatest._compatibility.builtins import *

from datatest._vendor.load_csv import load_csv

try:
    from StringIO import StringIO
except ImportError:
    StringIO = None


class TestLoadCsv(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(':memory:')
        connection.execute('PRAGMA synchronous=OFF')
        connection.isolation_level = None
        self.cursor = connection.cursor()

        self.original_cwd = os.path.abspath(os.getcwd())
        os.chdir(os.path.join(os.path.dirname(__file__), 'sample_files'))

    def tearDown(self):              # It would be best to use addCleanup()
        os.chdir(self.original_cwd)  # but it is not available in Python 2.6.

    @staticmethod
    def get_stream(string, encoding=None):
        """Accepts a string and returns a file-like stream object.

        In Python 2, Unicode files should be opened in binary-mode
        but in Python 3, they should be opened in text-mode. This
        function emulates the appropriate opening behavior.
        """
        fh = io.BytesIO(string)
        if sys.version_info[0] == 2:
            return fh
        return io.TextIOWrapper(fh, encoding=encoding)

    def test_encoding_with_stream(self):
        csvfile = self.get_stream((
            b'col1,col2\n'
            b'1,\xe6\n'  # '\xe6' -> æ (ash)
            b'2,\xf0\n'  # '\xf0' -> ð (eth)
            b'3,\xfe\n'  # '\xfe' -> þ (thorn)
        ), encoding='latin-1')
        load_csv(self.cursor, 'testtable1', csvfile, encoding='latin-1')

        expected = [
            ('1', chr(0xe6)),  # chr(0xe6) -> æ
            ('2', chr(0xf0)),  # chr(0xf0) -> ð
            ('3', chr(0xfe)),  # chr(0xfe) -> þ
        ]
        self.cursor.execute('SELECT col1, col2 FROM testtable1')
        self.assertEqual(list(self.cursor), expected)

    def test_encoding_with_file(self):
        path = 'sample_text_iso88591.csv'
        load_csv(self.cursor, 'testtable', path, encoding='latin-1')

        expected = [
            ('iso88591', chr(0xe6)),  # chr(0xe6) -> æ
        ]
        self.cursor.execute('SELECT col1, col2 FROM testtable')
        self.assertEqual(list(self.cursor), expected)

    def test_encoding_mismatch(self):
        path = 'sample_text_iso88591.csv'
        wrong_encoding = 'utf-8'  # <- Doesn't match file.

        with self.assertRaises(UnicodeDecodeError):
            load_csv(self.cursor, 'testtable', path, wrong_encoding)

    def test_fallback_with_stream(self):
        with warnings.catch_warnings(record=True):  # Catch warnings issued
            csvfile = self.get_stream((             # when running Python 2.
                b'col1,col2\n'
                b'1,\xe6\n'  # '\xe6' -> æ (ash)
                b'2,\xf0\n'  # '\xf0' -> ð (eth)
                b'3,\xfe\n'  # '\xfe' -> þ (thorn)
            ), encoding='latin-1')
            load_csv(self.cursor, 'testtable1', csvfile)  # <- No encoding arg.

        expected = [
            ('1', chr(0xe6)),  # chr(0xe6) -> æ
            ('2', chr(0xf0)),  # chr(0xf0) -> ð
            ('3', chr(0xfe)),  # chr(0xfe) -> þ
        ]
        self.cursor.execute('SELECT col1, col2 FROM testtable1')
        self.assertEqual(list(self.cursor), expected)

        def test_fallback_with_StringIO(self):
            if not StringIO:  # <- Python 2.x only.
                return

            csvfile = StringIO(
                b'col1,col2\n'
                b'1,\xe6\n'  # '\xe6' -> æ (ash)
                b'2,\xf0\n'  # '\xf0' -> ð (eth)
                b'3,\xfe\n'  # '\xfe' -> þ (thorn)
            )

            with warnings.catch_warnings(record=True):
                load_csv(self.cursor, 'testtable1', csvfile)

            expected = [
                ('1', chr(0xe6)),  # chr(0xe6) -> æ
                ('2', chr(0xf0)),  # chr(0xf0) -> ð
                ('3', chr(0xfe)),  # chr(0xfe) -> þ
            ]
            self.cursor.execute('SELECT col1, col2 FROM testtable1')
            self.assertEqual(list(self.cursor), expected)

    def test_fallback_with_file(self):
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter('always')
            path = 'sample_text_iso88591.csv'
            load_csv(self.cursor, 'testtable', path)  # <- No encoding arg.

        self.assertEqual(len(warning_list), 1)
        expected = "using fallback 'latin-1'"
        self.assertIn(expected, str(warning_list[0].message))

        expected = [
            ('iso88591', chr(0xe6)),  # chr(0xe6) -> æ
        ]
        self.cursor.execute('SELECT col1, col2 FROM testtable')
        self.assertEqual(list(self.cursor), expected)

    def test_fallback_with_exhaustible_object(self):
        """Exhaustible iterators and unseekable file-like objects
        can only be iterated over once. This means that the usual
        fallback behavior can not be applied and the function must
        raise an exception.
        """
        if not sys.version_info[0] == 2:
            return

        csvfile = self.get_stream((
            b'col1,col2\n'
            b'1,\xe6\n'  # '\xe6' -> æ (ash)
            b'2,\xf0\n'  # '\xf0' -> ð (eth)
            b'3,\xfe\n'  # '\xfe' -> þ (thorn)
        ), encoding='latin-1')
        generator = (x for x in csvfile)  # <- Make stream unseekable.

        with self.assertRaises(UnicodeDecodeError) as cm:
            load_csv(self.cursor, 'testtable', generator)

        error_message = str(cm.exception)
        self.assertIn('cannot attempt fallback', error_message.lower())
