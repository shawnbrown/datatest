"""Adds "validate" accessors to pandas DataFrame, Series, and Index."""
import inspect
from ._compatibility import contextlib
from .validation import ValidationError
from .validation import validate


class ValidationAccessor(object):
    def __init__(self, pandas_obj):
        self._data = pandas_obj

    # Note: Below, the try/except code is duplicated for every method because
    # using a shared method would create an additional traceback entry without
    # adding any useful information. This should be avoided--even at the cost
    # of some code duplication.

    def __call__(self, requirement, msg=None):
        try:
            return validate(self._data, requirement, msg=msg)
        except ValidationError as err:
            __tracebackhide__ = True
            err.__traceback__ = None
            err.__cause__ = None
            raise err

    def predicate(self, requirement, msg=None):
        """Check that elements satisfy predicate requirement."""
        try:
            return validate.predicate(self._data, requirement, msg=msg)
        except ValidationError as err:
            __tracebackhide__ = True
            err.__traceback__ = None
            err.__cause__ = None
            raise err

    def regex(self, requirement, flags=0, msg=None):
        """Check that elements match regex requirement."""
        try:
            return validate.regex(self._data, requirement, flags=flags, msg=msg)
        except ValidationError as err:
            __tracebackhide__ = True
            err.__traceback__ = None
            err.__cause__ = None
            raise err

    def approx(self, requirement, places=None, msg=None, delta=None):
        """Check that elements approximately match requirement."""
        try:
            return validate.approx(self._data, requirement, places=places, msg=msg, delta=delta)
        except ValidationError as err:
            __tracebackhide__ = True
            err.__traceback__ = None
            err.__cause__ = None
            raise err

    def fuzzy(self, requirement, cutoff=0.6, msg=None):
        """Check that strings are similar to requirement strings.
        Strings are considered similar if they measure equal to or
        greater than cutoff (default 0.6) as determined by the
        difflib.SequenceMatcher class (from the Standard Library).
        """
        try:
            return validate.fuzzy(self._data, requirement, cutoff=cutoff, msg=msg)
        except ValidationError as err:
            __tracebackhide__ = True
            err.__traceback__ = None
            err.__cause__ = None
            raise err

    def interval(self, min=None, max=None, msg=None):
        """Check that element values are within the given interval."""
        try:
            return validate.interval(self._data, min=min, max=max, msg=msg)
        except ValidationError as err:
            __tracebackhide__ = True
            err.__traceback__ = None
            err.__cause__ = None
            raise err

    def set(self, requirement, msg=None):
        """Check that element set equals requirement set."""
        try:
            return validate.set(self._data, requirement, msg=msg)
        except ValidationError as err:
            __tracebackhide__ = True
            err.__traceback__ = None
            err.__cause__ = None
            raise err

    def subset(self, requirement, msg=None):
        """Check that element set contains requirement subset."""
        try:
            return validate.subset(self._data, requirement, msg=msg)
        except ValidationError as err:
            __tracebackhide__ = True
            err.__traceback__ = None
            err.__cause__ = None
            raise err

    def superset(self, requirement, msg=None):
        """Check that element set is contained in requirement superset."""
        try:
            return validate.superset(self._data, requirement, msg=msg)
        except ValidationError as err:
            __tracebackhide__ = True
            err.__traceback__ = None
            err.__cause__ = None
            raise err

    def unique(self, msg=None):
        """Check that elements are unique."""
        try:
            return validate.unique(self._data, msg=msg)
        except ValidationError as err:
            __tracebackhide__ = True
            err.__traceback__ = None
            err.__cause__ = None
            raise err

    def order(self, requirement, msg=None):
        """Check that elements match the relative order of requirement
        elements.
        """
        try:
            return validate.order(self._data, requirement, msg=msg)
        except ValidationError as err:
            __tracebackhide__ = True
            err.__traceback__ = None
            err.__cause__ = None
            raise err


# From the documented Pandas API, it's not entirely clear that
# a single class is intended to be registered as an accessor on
# multiple pandas objects. For reliability, we define a separate
# subclass for each pandas object being extended. While it would
# be more concise to call core.accessor._register_accessor()
# directly, that is not a user facing interface--DO NOT USE IT.

class ValidateDataFrame(ValidationAccessor):
    """Check that values in DataFrame satisfy the *requirement*."""
    pass


class ValidateSeries(ValidationAccessor):
    """Check that values in Series satisfy the *requirement*."""
    pass


class ValadateIndex(ValidationAccessor):
    """Check that values in Index satisfy the *requirement*."""
    pass


##############################################
# Import pandas and register custom accessors.
##############################################

def register_accessors():
    """Register "validate" accessors for pandas :class:`DataFrame
    <pandas.DataFrame>`, :class:`Series <pandas.Series>`, and
    :class:`Index <pandas.Index>` objects:

    .. code-block:: python
        :emphasize-lines: 4

        import pandas as pd
        import datatest as dt

        dt.register_accessors()
        ...

    After registering, the "validate" accessor maps calls to
    :func:`validate`.
    """
    global ValidateDataFrame
    global ValidateSeries
    global ValadateIndex

    try:
        import pandas

        try:
            accessor = getattr(pandas.DataFrame, 'validate', None)
            if not (accessor and issubclass(accessor, ValidateDataFrame)):
                decorator = pandas.api.extensions.register_dataframe_accessor('validate')
                ValidateDataFrame = decorator(ValidateDataFrame)

            accessor = getattr(pandas.Series, 'validate', None)
            if not (accessor and issubclass(accessor, ValidateSeries)):
                decorator = pandas.api.extensions.register_series_accessor('validate')
                ValidateSeries = decorator(ValidateSeries)

            accessor = getattr(pandas.Index, 'validate', None)
            if not (accessor and issubclass(accessor, ValadateIndex)):
                decorator = pandas.api.extensions.register_index_accessor('validate')
                ValadateIndex = decorator(ValadateIndex)

        except AttributeError:
            import warnings
            message = 'unable to register accessors; extension API unavailable'
            warnings.warn(message)

    except ImportError:
        import warnings
        message = 'unable to register accessors; unable to import pandas'
        warnings.warn(message)
