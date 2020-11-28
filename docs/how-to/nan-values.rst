
.. currentmodule:: datatest

.. meta::
    :description: How to deal with NaN values.
    :keywords: datatest, NaN, not a number, np.nan, math.nan


###########################
How to Deal With NaN Values
###########################

.. sidebar:: IEEE 754

    While the behavior of NaN values can seem strange, it's actually
    the result of an intentionally designed specification. The behavior
    was standardized in :abbr:`IEEE 754 (IEEE Standard for Floating-Point
    Arithmetic)`, a technical standards document first published in
    1985 and implemented by many popular programming languages (including
    Python).

When checking certain types of data, you may encounter NaN values.
Working with NaNs can be frustrating because they don't always act
as one might expect.

About NaN values:

* NaN is short for "Not a Number".
* NaN values represent undefined or unrepresentable results
  from certain mathematical operations.
* Mathematical operations involving a NaN will either return a
  NaN or raise an exception.
* Comparisons involving a NaN will return False.


Accepting NaN Differences
=========================

If validation fails and returns NaN differences, you can accept
them as you would any other difference:

.. code-block:: python
    :emphasize-lines: 8

    from datatest import validate, accepted, Extra
    from math import nan


    data = [5, 6, float('nan')]
    requirement = {5, 6}

    with accepted(Extra(nan)):
        validate(data, requirement)

Like other values, NaNs can also be accepted as part of a list,
set, or mapping of differences:

.. code-block:: python
    :emphasize-lines: 8

    from datatest import validate, accepted, Extra, Missing
    from math import nan


    data = [5, 6, float('nan')]
    requirement = {5, 6, 7}

    known_issues = accepted([Missing(7), Extra(nan)])

    with known_issues:
        validate(data, requirement)

.. note::

    The :py:data:`math.nan` value is new in Python 3.5. NaN values can
    also be created in any Python version with the :py:class:`float`
    constructor ``float('nan')``.


Dropping NaNs Before Validation
===============================

Sometimes it's OK to ignore NaN values entirely. If this is
appropriate in your circumstance, you can simply remove all
NaN records and validate the remaining data.

If you're using Pandas, you can call the |Series.dropna| and
|DataFrame.dropna| methods to drop records that contain NaN
values:

.. |Series.dropna| replace:: :meth:`Series.dropna() <pandas.Series.dropna>`
.. |DataFrame.dropna| replace:: :meth:`DataFrame.dropna() <pandas.DataFrame.dropna>`

.. code-block:: python
    :emphasize-lines: 6

    from datatest import validate
    import pandas as pd


    data = pd.Series([1, 1, 2, 2, float('nan')], dtype='float64')
    data = data.dropna()  # Drop records with NaN values.
    requirement = {1, 2}

    validate(data, requirement)


An example that does not rely on Pandas:

.. code-block:: python
    :emphasize-lines: 6

    from datatest import validate
    from math import isnan


    data = [1, 1, 2, 2, float('nan')]
    data = [x for x in data if not isnan(x)]  # Drop records with NaN values.
    requirement = {1, 2}

    validate(data, requirement)


Validating NaN Values
=====================

You may want to check that NaNs are part of a required set instead
of accepting them as differences. The most robust way to do this is
by replacing NaN values with a special token before validation. Using
NaN values directly can be frought with problems and should usually
be avoided.

If you're using Pandas, you can call the |Series.fillna| and
|DataFrame.fillna| methods to replace NaNs with a different value.

.. |Series.fillna| replace:: :meth:`Series.fillna() <pandas.Series.fillna>`
.. |DataFrame.fillna| replace:: :meth:`DataFrame.fillna() <pandas.DataFrame.fillna>`


Below, we define a custom ``NanToken`` value and use it to replace
actual NaN values:

.. code-block:: python
    :emphasize-lines: 14

    from datatest import validate
    import pandas as pd
    import numpy as np


    class NanToken(object):
        def __repr__(self):
            return self.__class__.__name__

    NanToken = NanToken()


    data = pd.Series([1, 1, 2, 2, np.nan], dtype='float64')
    data = data.fillna(NanToken)  # Replace NaNs with NanToken.

    requirement = {1, 2, NanToken}

    validate(data, requirement)


An example that does not rely on Pandas:

.. code-block:: python
    :emphasize-lines: 20

    from datatest import validate
    from math import isnan


    class NanToken(object):
        def __repr__(self):
            return self.__class__.__name__

    NanToken = NanToken()


    def nan_to_token(x):
        try:
            return NanToken if isnan(x) else x
        except TypeError:
            return x


    data = [1, 1, 2, 2, float('nan')]
    data = [nan_to_token(x) for x in data]  # Replace NaNs with NanToken.

    requirement = {1, 2, NanToken}

    validate(data, requirement)


A Deeper Understanding
======================

Equality: NaN ≠ NaN
-------------------

NaN values don't compare as equal to anything---even themselves::

    >>> x = float('nan')
    >>> x == x
    False


To check if a value is NaN, it's common for modules and packages
to provide a function for this purpose (e.g., :py:func:`math.isnan`,
:obj:`numpy.isnan() <numpy.isnan>`, :func:`pandas.isna`, etc.)::

    >>> import math
    >>> x = float('nan')
    >>> math.isnan(x)
    True


While NaN values cannot be compared directly, they *can* be compared
as part of a difference object. In fact, difference comparisons treat
all NaN values as equal---even when the underlying type is different::

    >>> from datatest import Invalid
    >>> import decimal, math, numpy

    >>> Invalid(math.nan) == Invalid(float('nan'))
    True
    >>> Invalid(math.nan) == Invalid(complex('nan'))
    True
    >>> Invalid(math.nan) == Invalid(decimal.Decimal('nan'))
    True
    >>> Invalid(math.nan) == Invalid(numpy.nan)
    True
    >>> Invalid(math.nan) == Invalid(numpy.float32('nan'))
    True
    >>> Invalid(math.nan) == Invalid(numpy.float64('nan'))
    True


Identity: NaN is NaN, Except When it Isn't
------------------------------------------

Some packages provide a NaN constant that can be referenced in
user code (e.g., :py:data:`math.nan` and :py:data:`numpy.nan`).
While it may be tempting to use these constants to check for
matching NaN values, this approach is not reliable in practice.

To optimize performance, Numpy and Pandas must strictly manage the
memory layouts of the data they contain. When :data:`numpy.nan` is
inserted into an :class:`ndarray <numpy.ndarray>` or :class:`Series
<pandas.Series>`, the value is coerced into a compatible ``dtype``
when necessary. When a NaN's type is coerced, a separate instance
is created and the ability to match using the ``is`` operator
no longer works as you might expect::

    >>> import pandas as pd
    >>> import numpy as np

    >>> np.nan is np.nan
    True

    >>> s = pd.Series([10, 11, np.nan])
    >>> s[2]
    nan
    >>> s[2] is np.nan
    False


We can verify that the types are now different:

    >>> type(np.nan)
    float
    >>> type(s[2])
    float64

Generally speaking, it is not safe to assume that NaN is NaN.
This means that---for reliable validation---it's best to remove
NaN records entirely or replace them with some other value.

