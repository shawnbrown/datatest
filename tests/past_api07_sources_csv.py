# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import sys

from . import _io as io
from . import _unittest as unittest
from .common import MkdtempTestCase
from .common import make_csv_file

from .mixins import CountTests
from .mixins import OtherTests

from datatest.__past__.api07_sources import CsvSource


class TestCsvSource(OtherTests, unittest.TestCase):
    def setUp(self):
        fh = make_csv_file(self.fieldnames, self.testdata)
        self.datasource = CsvSource(fh)

    def test_empty_file(self):
        pass
        #file exists but is empty should fail, too!


class TestCsvSource_FileHandling(unittest.TestCase):
    @staticmethod
    def _get_filelike(string, encoding=None):
        """Return file-like stream object."""
        filelike = io.BytesIO(string)
        if encoding and sys.version >= '3':
            filelike = io.TextIOWrapper(filelike, encoding=encoding)
        return filelike

    def test_filelike_object(self):
        fh = self._get_filelike(b'label1,label2,value\n'
                                b'a,x,18\n'
                                b'a,x,13\n'
                                b'a,y,20\n'
                                b'a,z,15\n', encoding='ascii')
        CsvSource(fh)  # Pass without error.

        fh = self._get_filelike(b'label1,label2,value\n'
                                b'a,x,18\n'
                                b'a,x,13\n'
                                b'a,\xc3\xb1,20\n'  # \xc3\xb1 is utf-8 literal for ñ
                                b'a,z,15\n', encoding='utf-8')
        CsvSource(fh)  # Pass without error.

        fh = self._get_filelike(b'label1,label2,value\n'
                                b'a,x,18\n'
                                b'a,x,13\n'
                                b'a,\xf1,20\n'  # '\xf1' is iso8859-1 for ñ
                                b'a,z,15\n', encoding='iso8859-1')
        CsvSource(fh, encoding='iso8859-1')  # Pass without error.

    def test_bad_filelike_object(self):
        with self.assertRaises(UnicodeDecodeError):
            fh = self._get_filelike(b'label1,label2,value\n'
                                    b'a,x,18\n'
                                    b'a,x,13\n'
                                    b'a,\xf1,20\n'  # '\xf1' is iso8859-1 for ñ, not utf-8!
                                    b'a,z,15\n', encoding='utf-8')
            CsvSource(fh, encoding='utf-8')  # Raises exception!


class TestCsvSource_ActualFileHandling(MkdtempTestCase):
    def test_utf8(self):
        with open('utf8file.csv', 'wb') as fh:
            filecontents = (b'label1,label2,value\n'
                            b'a,x,18\n'
                            b'a,x,13\n'
                            b'a,\xc3\xb1,20\n'  # \xc3\xb1 is utf-8 literal for ñ
                            b'a,z,15\n')
            fh.write(filecontents)
            abspath = os.path.abspath(fh.name)

        CsvSource(abspath)  # Pass without error.

        CsvSource(abspath, encoding='utf-8')  # Pass without error.

        msg = 'If wrong encoding is specified, should raise exception.'
        with self.assertRaises(UnicodeDecodeError, msg=msg):
            CsvSource(abspath, encoding='ascii')

    def test_iso88591(self):
        with open('iso88591file.csv', 'wb') as fh:
            filecontents = (b'label1,label2,value\n'
                            b'a,x,18\n'
                            b'a,x,13\n'
                            b'a,\xf1,20\n'  # '\xf1' is iso8859-1 for ñ, not utf-8!
                            b'a,z,15\n')
            fh.write(filecontents)
            abspath = os.path.abspath(fh.name)

        CsvSource(abspath, encoding='iso8859-1')  # Pass without error.

        msg = ('When encoding is unspecified, tries UTF-8 first then '
               'fallsback to ISO-8859-1 and raises a Warning.')
        with self.assertWarns(UserWarning, msg=msg):
            CsvSource(abspath)

        msg = 'If wrong encoding is specified, should raise exception.'
        with self.assertRaises(UnicodeDecodeError, msg=msg):
            CsvSource(abspath, encoding='utf-8')

    def test_file_handle(self):
        if sys.version_info[0] > 2:
            correct_mode = 'rt'  # Python 3, requires text-mode.
            incorrect_mode = 'rb'
        else:
            correct_mode = 'rb'  # Python 2, requires binary-mode.
            incorrect_mode = 'rt'

        filename = 'utf8file.csv'
        with open(filename, 'wb') as fh:
            filecontents = (b'label1,label2,value\n'
                            b'a,x,18\n'
                            b'a,x,13\n'
                            b'a,\xc3\xb1,20\n'  # \xc3\xb1 is utf-8 literal for ñ
                            b'a,z,15\n')
            fh.write(filecontents)

        with open(filename, correct_mode) as fh:
            CsvSource(fh, encoding='utf-8')  # Pass without error.

        with self.assertRaises(Exception):
            with open(filename, incorrect_mode) as fh:
                CsvSource(fh, encoding='utf-8')  # Raise exception.


class TestCsvSource_fmtparams(unittest.TestCase):
    @staticmethod
    def _get_filelike(string, encoding=None):
        """Return file-like stream object."""
        filelike = io.BytesIO(string)
        if encoding and sys.version >= '3':
            filelike = io.TextIOWrapper(filelike, encoding=encoding)
        return filelike

    def test_fmtparams(self):
        fh = self._get_filelike(b'label1\tlabel2\tvalue\n'
                                b'a\tx\t18\n'
                                b'a\tx\t13\n'
                                b'a\ty\t20\n'
                                b'a\tz\t15\n', encoding='ascii')

        # Load using valid fmtparams option ("delimiter")
        source = CsvSource(fh, delimiter='\t')

        result = list(source.__iter__())
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '18'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
        ]
        self.assertEqual(result, expected)
