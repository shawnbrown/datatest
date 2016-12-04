# -*- coding: utf-8 -*-
import pprint


class DataError(AssertionError):
    """Raised when :meth:`assertValid` finds differences between *data*
    and *requirement*.
    """
    def __init__(self, msg, differences, subject=None, required=None):
        """Initialize self, store *differences* for later reference."""
        if not differences:
            raise ValueError('Missing differences.')
        self._differences = differences
        self.msg = msg
        self.subject = str(subject)    # Subject data source.
        self.required = str(required)  # Required object or reference source.
        self._verbose = False  # <- Set by DataTestResult if verbose.

        return AssertionError.__init__(self, msg)

    @property
    def differences(self):
        """An iterable (list or dict) of differences."""
        return self._differences

    def __repr__(self):
        return self.__class__.__name__ + ': ' + self.__str__()

    def __str__(self):
        diff = pprint.pformat(self.differences, width=1)
        if any([diff.startswith('{') and diff.endswith('}'),
                diff.startswith('[') and diff.endswith(']'),
                diff.startswith('(') and diff.endswith(')')]):
            diff = diff[1:-1]

        if self._verbose:
            msg_extras = '\n\nSUBJECT:\n{0}\nREQUIRED:\n{1}'
            msg_extras = msg_extras.format(self.subject, self.required)
        else:
            msg_extras = ''

        return '{0}:\n {1}{2}'.format(self.msg, diff, msg_extras)
