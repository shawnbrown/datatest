
.. currentmodule:: datatest

.. meta::
    :description: How to validate negative matches.
    :keywords: datatest, negative match


################################
How to Validate Negative Matches
################################

Sometimes you want to check that data is **not** equal to a specific
value. There are a few different ways to perform this type of negative
matching.


Helper Function
===============

One obvious way to check for a negative match is to define a helper
function that checks for ``!=`` to a given value:

.. code-block:: python
    :linenos:

    from datatest import validate

    data = [...]

    def not_bar(x):
        return x != 'bar'

    validate(data, not_bar)


Inverted Predicate
==================

Datatest provides a :class:`Predicate` class for handling different
kinds of matching. You can invert a Predicate's behavior using the
inversion operator, ``~``:

.. code-block:: python
    :emphasize-lines: 4
    :linenos:

    from datatest import validate, Predicate

    data = [...]
    validate(data, ~Predicate('bar'))


Functional Style
================

If you are accustomed to programming in a functional style, you
could perform a negative match using :func:`functools.partial` and
:func:`operator.ne`:

.. code-block:: python
    :emphasize-lines: 6
    :linenos:

    from functools import partial
    from operator import ne
    from datatest import validate

    data = [...]
    validate(data, partial(ne, 'bar'))

