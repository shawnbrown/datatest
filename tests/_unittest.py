"""compatibility layer for unittest (Python standard library)"""
from __future__ import absolute_import
from unittest import *
import sys as _sys


try:
    TestCase.assertIn  # New in 2.7/3.1
    #TestCase.assertNotIn
except AttributeError:
    def _assertIn(self, member, container, msg=None):
        """Just like self.assertTrue(a in b), but with a nicer default
        message.
        """
        if member not in container:
            standardMsg = '%r not found in %r' % (member, container)
            self.fail(self._formatMessage(msg, standardMsg))
    TestCase.assertIn = _assertIn


try:
    TestCase.assertIsNone  # New in 2.7/3.1
    #TestCase.assertIsNotNone
except AttributeError:
    def _assertIsNone(self, obj, msg=None):
        """Same as self.assertTrue(obj is None), with a nicer default
        message.
        """
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
    TestCase.assertIs  # New in 2.7
except AttributeError:
    def _assertIs(self, expr1, expr2, msg=None):
        """Just like self.assertTrue(a is b), but with a nicer default
        message.
        """
        if not expr1 is expr2:
            standardMsg = '%s is not %s' % (safe_repr(expr1), safe_repr(expr2))
            self.fail(self._formatMessage(msg, standardMsg))
    TestCase.assertIs = _assertIs

    def _assertIsNot(self, expr1, expr2, msg=None):
        """Just like self.assertTrue(a is not b), but with a nicer
        default message.
        """
        if not expr1 is not expr2:
            standardMsg = '%s is not %s' % (safe_repr(expr1), safe_repr(expr2))
            self.fail(self._formatMessage(msg, standardMsg))
    TestCase.assertIsNot = _assertIsNot


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
            """Fail the test unless the text matches the regular
            expression.
            """
            if isinstance(expected_regexp, _basestring):
                expected_regexp = _compile(expected_regexp)
            if not expected_regexp.search(text):
                msg = msg or "Regexp didn't match"
                msg = '%s: %r not found in %r' % (msg, expected_regexp.pattern, text)
                raise self.failureException(msg)
        TestCase.assertRegex = _assertRegex

        def _assertNotRegex(self, text, unexpected_regexp, msg=None):
            """Fail the test if the text matches the regular
            expression.
            """
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
            """A context manager used to implement
            TestCase.assertRaises* methods.
            """
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

try:
    TestCase.assertRaisesRegex  # Renamed in 3.2 (previously assertRaisesRegexp)
except AttributeError:
    TestCase.assertRaisesRegex = TestCase.assertRaisesRegexp  # New in 2.7


try:
    _sys.modules['unittest'].case._AssertWarnsContext  # New in 3.2
except AttributeError:
    import warnings as _warnings
    class _AssertWarnsContext(object):
        """A context manager used to implement TestCase.assertWarns*
        methods.
        """
        def __init__(self, expected, test_case, callable_obj=None,
                     expected_regex=None):
            self.expected = expected
            self.test_case = test_case
            if callable_obj is not None:
                try:
                    self.obj_name = callable_obj.__name__
                except AttributeError:
                    self.obj_name = str(callable_obj)
            else:
                self.obj_name = None
            if isinstance(expected_regex, (bytes, str)):
                expected_regex = re.compile(expected_regex)
            self.expected_regex = expected_regex
            self.msg = None

        def _raiseFailure(self, standardMsg):
            msg = self.test_case._formatMessage(self.msg, standardMsg)
            raise self.test_case.failureException(msg)

        def handle(self, name, callable_obj, args, kwargs):
            if callable_obj is None:
                self.msg = kwargs.pop('msg', None)
                return self
            with self:
                callable_obj(*args, **kwargs)

        def __enter__(self):
            for v in _sys.modules.values():
                if getattr(v, '__warningregistry__', None):
                    v.__warningregistry__ = {}
            self.warnings_manager = _warnings.catch_warnings(record=True)
            self.warnings = self.warnings_manager.__enter__()
            _warnings.simplefilter("always", self.expected)
            return self

        def __exit__(self, exc_type, exc_value, tb):
            self.warnings_manager.__exit__(exc_type, exc_value, tb)
            if exc_type is not None:
                return
            try:
                exc_name = self.expected.__name__
            except AttributeError:
                exc_name = str(self.expected)
            first_matching = None
            for m in self.warnings:
                w = m.message
                if not isinstance(w, self.expected):
                    continue
                if first_matching is None:
                    first_matching = w
                if (self.expected_regex is not None and
                    not self.expected_regex.search(str(w))):
                    continue
                self.warning = w
                self.filename = m.filename
                self.lineno = m.lineno
                return
            if first_matching is not None:
                self._raiseFailure('"{}" does not match "{}"'.format(
                         self.expected_regex.pattern, str(first_matching)))
            if self.obj_name:
                self._raiseFailure("{} not triggered by {}".format(exc_name,
                                                                   self.obj_name))
            else:
                self._raiseFailure("{} not triggered".format(exc_name))

    def _assertWarns(self, expected_warning, callable_obj=None, *args, **kwargs):
        context = _AssertWarnsContext(expected_warning, self, callable_obj)
        return context.handle('assertWarns', callable_obj, args, kwargs)
    TestCase.assertWarns = _assertWarns


try:
    skip  # New in 2.7 and 3.1
    skipIf
    skipUnless
except NameError:
    # The following code was adapted from the Python 2.7 standard library.
    import functools

    def _id(obj):
        return obj

    def skip(reason):
        """Unconditionally skip a test."""
        import types
        def decorator(test_item):
            #if not isinstance(test_item, (type, types.ClassType)):
            #    @functools.wraps(test_item)
            #    def skip_wrapper(*args, **kwargs):
            #        raise SkipTest(reason)
            #    test_item = skip_wrapper
            #
            #test_item.__unittest_skip__ = True
            #test_item.__unittest_skip_why__ = reason
            #return test_item

            # In older version of Python, tracking skipped tests is
            # problematic since the test loader and runner handle this
            # internally.  For this reason, this compatibility wrapper
            # simply wraps skipped tests in a functoin that passes
            # silently:
            @functools.wraps(test_item)
            def skip_wrapper(*args, **kwargs):
                pass
            return skip_wrapper
        return decorator

    def skipIf(condition, reason):
        """Skip a test if the condition is true."""
        if condition:
            return skip(reason)
        return _id

    def skipUnless(condition, reason):
        """Skip a test unless the condition is true."""
        if not condition:
            return skip(reason)
        return _id
