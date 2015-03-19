"""unittest compatibility layer."""
import sys as _sys
from unittest import *

try:
    TestCase.assertIn  # New in 2.7/3.1
    #TestCase.assertNotIn
except AttributeError:
    def _assertIn(self, member, container, msg=None):
        """Just like self.assertTrue(a in b), but with a nicer default message."""
        if member not in container:
            standardMsg = '%r not found in %r' % (member, container)
            self.fail(self._formatMessage(msg, standardMsg))
    TestCase.assertIn = _assertIn


try:
    TestCase.assertIsNone  # New in 2.7/3.1
    #TestCase.assertIsNotNone
except AttributeError:
    def _assertIsNone(self, obj, msg=None):
        """Same as self.assertTrue(obj is None), with a nicer default message."""
        if obj is not None:
            standardMsg = '%s is not None' % (safe_repr(obj),)
            self.fail(self._formatMessage(msg, standardMsg))
    TestCase.assertIsNone = _assertIsNone

    #def _assertIsNotNone(self, obj, msg=None):
    #    """Included for symmetry with assertIsNone."""
    #    if obj is None:
    #        standardMsg = 'unexpectedly None'
    #        self.fail(self._formatMessage(msg, standardMsg))
    #TestCase.assertIsNotNone = _assertIsNotNone


try:
    TestCase.assertSetEqual  # New in 2.7/3.
except AttributeError:
    def _assertSetEqual(self, set1, set2, msg=None):
        try:
            difference1 = set1.difference(set2)
        #except TypeError, e:
        #    self.fail('invalid type when attempting set difference: %s' % e)
        except TypeError:
            self.fail('invalid type when attempting set difference')
        #except AttributeError, e:
        #    self.fail('first argument does not support set difference: %s' % e)
        except AttributeError:
            self.fail('first argument does not support set difference')
        try:
            difference2 = set2.difference(set1)
        #except TypeError, e:
        #    self.fail('invalid type when attempting set difference: %s' % e)
        except TypeError:
            self.fail('invalid type when attempting set difference')
        #except AttributeError, e:
        #    self.fail('second argument does not support set difference: %s' % e)
        except AttributeError:
            self.fail('second argument does not support set difference')
        if not (difference1 or difference2):
            return
        lines = []
        if difference1:
            lines.append('Items in the first set but not the second:')
            for item in difference1:
                lines.append(repr(item))
        if difference2:
            lines.append('Items in the second set but not the first:')
            for item in difference2:
                lines.append(repr(item))
        standardMsg = '\n'.join(lines)
        self.fail(self._formatMessage(msg, standardMsg))
    TestCase.assertSetEqual = _assertSetEqual


try:
    TestCase.assertIsInstance  # New in 3.2
except AttributeError:
    def _assertIsInstance(self, obj, cls, msg=None):
        """Same as self.assertTrue(isinstance(obj, cls)), with a nicer
        default message."""
        if not isinstance(obj, cls):
            standardMsg = '%s is not an instance of %r' % (safe_repr(obj), cls)
            self.fail(self._formatMessage(msg, standardMsg))
    TestCase.assertIsInstance = _assertIsInstance


try:
    TestCase._formatMessage
except AttributeError:
    def _formatMessage(self, msg, standardMsg):
        if not self.longMessage:
            return msg or standardMsg
        if msg is None:
            return standardMsg
        try:
            return '%s : %s' % (standardMsg, msg)
        except UnicodeDecodeError:
            return  '%s : %s' % (safe_repr(standardMsg), safe_repr(msg))
    TestCase.longMessage = True
    TestCase._formatMessage = _formatMessage


try:
    TestCase.assertRegex  # Renamed in 3.2 (previously assertRegexpMatches)
    TestCase.assertNotRegex
except AttributeError:
    try:
        TestCase.assertRegex = TestCase.assertRegexpMatches
        TestCase.assertNotRegex = TestCase.assertNotRegexpMatches
    except AttributeError:
        from re import compile as _compile

        try:
            _basestring = basestring
        except NameError:
            _basestring = str

        def _assertRegex(self, text, expected_regexp, msg=None):
            """Fail the test unless the text matches the regular expression."""
            if isinstance(expected_regexp, _basestring):
                expected_regexp = _compile(expected_regexp)
            if not expected_regexp.search(text):
                msg = msg or "Regexp didn't match"
                msg = '%s: %r not found in %r' % (msg, expected_regexp.pattern, text)
                raise self.failureException(msg)
        TestCase.assertRegex = _assertRegex

        def _assertNotRegex(self, text, unexpected_regexp, msg=None):
            """Fail the test if the text matches the regular expression."""
            if isinstance(unexpected_regexp, _basestring):
                unexpected_regexp = _compile(unexpected_regexp)
            match = unexpected_regexp.search(text)
            if match:
                msg = msg or 'Regexp matched'
                msg = '%s: %r matches %r in %r' % (msg,
                                                   text[match.start():match.end()],
                                                   unexpected_regexp.pattern,
                                                   text)
                raise self.failureException(msg)
        TestCase.assertNotRegex = _assertNotRegex


try:
    _sys.modules['unittest'].case._AssertRaisesContext  # New in 2.7
except AttributeError:
    try:
        _sys.modules['unittest']._AssertRaisesContext  # Changed briefly (for 3.1 only)
    except AttributeError:
        # The following code was adapted from the Python 2.7 Standard Library.
        import re as _re
        class _AssertRaisesContext(object):
            """A context manager used to implement TestCase.assertRaises* methods."""
            def __init__(self, expected, test_case, expected_regexp=None):
                self.expected = expected
                self.failureException = test_case.failureException
                self.expected_regexp = expected_regexp

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, tb):
                if exc_type is None:
                    try:
                        exc_name = self.expected.__name__
                    except AttributeError:
                        exc_name = str(self.expected)
                    raise self.failureException(
                        "{0} not raised".format(exc_name))
                if not issubclass(exc_type, self.expected):
                    # let unexpected exceptions pass through
                    return False
                self.exception = exc_value # store for later retrieval
                if self.expected_regexp is None:
                    return True
                expected_regexp = self.expected_regexp
                if isinstance(expected_regexp, basestring):
                    expected_regexp = _re.compile(expected_regexp)
                if not expected_regexp.search(str(exc_value)):
                    raise self.failureException('"%s" does not match "%s"' %
                             (expected_regexp.pattern, str(exc_value)))
                return True

        def _assertRaises(self, excClass, callableObj=None, *args, **kwargs):
            context = _AssertRaisesContext(excClass, self)
            if callableObj is None:
                return context
            with context:
                callableObj(*args, **kwargs)

        def _assertRaisesRegexp(self, expected_exception, expected_regexp,
                                callable_obj=None, *args, **kwargs):
            context = _AssertRaisesContext(expected_exception, self, expected_regexp)
            if callable_obj is None:
                return context
            with context:
                callable_obj(*args, **kwargs)

        TestCase.assertRaises = _assertRaises
        TestCase.assertRaisesRegexp = _assertRaisesRegexp

