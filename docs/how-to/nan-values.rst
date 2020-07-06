
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
    :emphasize-lines: 7

    from datatest import validate, accepted, Extra
    from math import nan

    data = [5, 6, float('nan')]
    requirement = {5, 6}

    with accepted(Extra(nan)):
        validate(data, requirement)

Like other values, NaNs can also be accepted as part of a list,
set, or mapping of differences:

.. code-block:: python
    :emphasize-lines: 7-8

    from datatest import validate, accepted, Extra, Missing
    from math import nan

    data = [5, 6, float('nan')]
    requirement = {5, 6, 7}

    known_issues = accepted([Missing(7), Extra(nan)])
    with known_issues:
        validate(data, requirement)

.. note::

    The :data:`math.nan` value is new in Python 3.5. NaN values can
    also be created in any Python version with the :py:class:`float`
    constructor ``float('nan')``.


Validating NaN Values
=====================

You may want to check that NaNs are part of a required set instead
of accepting them as differences. The most robust way to do this is
by replacing NaN values with a special token before validation. Using
NaN values directly can be frought with problems and should usually
be avoided.

If you are using Pandas, you can use the ``fillna()`` method to
replace NaNs with a token value:

.. code-block:: python
    :emphasize-lines: 12,13

    from datatest import validate
    import pandas as pd
    import numpy as np

    nantoken = type(
        'nantoken',
        (object,),
        {'__repr__': (lambda x: '<nantoken>')},
    )()

    data = pd.Series([1, 1, 2, 2, np.float64('nan')], dtype='float64')
    data = data.fillna(nantoken)    # <- Replace NaNs with nantoken.
    requirement = {1, 2, nantoken}  # <- Use nantoken as required value.

    validate(data, requirement)


An example that does not rely on Pandas:

.. code-block:: python
    :emphasize-lines: 17,18

    from datatest import validate
    from math import isnan

    nantoken = type(
        'nantoken',
        (object,),
        {'__repr__': (lambda x: '<nantoken>')},
    )()

    def nan_to_token(x):
        try:
            return nantoken if isnan(x) else x
        except TypeError:
            return x

    data = [1, 1, 2, 2, float('nan')]
    data = [nan_to_token(x) for x in data]  # <- Replace NaNs with nantoken.
    requirement = {1, 2, nantoken}          # <- Use nantoken as required value.

    validate(data, requirement)


Dropping NaNs Before Validation
===============================

Sometimes it's OK to ignore NaN values entirely. If this is
appropriate in your circumstance, you can simply remove all
NaN records and validate the remaining data.

If you are using Pandas, you can use the ``dropna()`` method to
drop records that contain NaN values:

.. code-block:: python
    :emphasize-lines: 5

    from datatest import validate
    import pandas as pd

    data = pd.Series([1, 1, 2, 2, float('nan')], dtype='float64')
    data = data.dropna()  # <- Drop records with NaN values.
    requirement = {1, 2}

    validate(data, requirement)


An example that does not rely on Pandas:

.. code-block:: python
    :emphasize-lines: 5

    from datatest import validate
    from math import isnan

    data = [1, 1, 2, 2, float('nan')]
    data = [x for x in data if not isnan(x)]  # <- Drop records with NaN values.
    requirement = {1, 2}

    validate(data, requirement)


A Deeper Understanding
======================

Equality: NaN ≠ NaN
-------------------

NaN values don't compare as equal to anything---even themselves.
To check if a value is NaN, it's common for modules and packages
to provide a function for this purpose:

* :py:func:`math.isnan` (from the Python Standard Library)
* :func:`numpy.isnan`
* :func:`pandas.isnan`

While NaN values cannot be compared directly, they *can* be compared
as part of a difference object. In fact, difference comparisons treat
all NaN values as equal---even when the underlying type is different::

    >>> from datatest import Invalid
    >>> import decimal, math, numpy
    >>>
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


Identity: NaN *is not* NaN (for the most part)
----------------------------------------------

Some packages provide a NaN constant that can be referenced in
user code (e.g., :py:data:`math.nan` and :py:data:`numpy.nan`).
While it may be tempting to use these constants to check for
matching NaN values, this approach is not reliable in practice.

To optimize performance, Numpy and Pandas must tightly controll
their internal data representations. When :data:`numpy.nan` is
inserted into an :class:`array <numpy.array>` or :class:`Series
<pandas.Series>`, the value is coerced into a compatible ``dtype``
when necessary. When a NaN's type is coerced, a separate instance
is created and the ability to match using the ``is`` operator
no longer works as you might expect::

    >>> import pandas as pd
    >>> import numpy as np
    >>>
    >>> s = pd.Series([10, 11, 12])
    >>>
    >>> s[2] = np.nan
    >>> s[2] is np.nan
    False


You can see that the values have different types::

    >>> type(np.nan)
    float
    >>> type(s[2])
    float64

Generally speaking, it is not safe to assume that NaN is NaN.
This means that---for reliable validation---it's best to remove
NaN records entirely or replace them with some other value.

