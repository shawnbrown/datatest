
.. currentmodule:: datatest

.. meta::
    :description: Examples showing how to use datatest for data pipeline
                  validation.
    :keywords: python, data, pipeline, validation


########################
Data Pipeline Validation
########################

Datatest can be used to validate data as it flows through a data
pipeline. This can be useful in a production environment because
the data coming into a pipeline can change in unexpected ways. An
up-stream provider could alter its format, the quality of a data
source could degrade over time, previously unheard-of errors or
missing data could be introduced, etc.

Well-structured pipelines are made of discrete, independent steps
where the output of one step becomes the input of the next step.
In the simplest case, the steps themselves can be functions. And
in a pipeline framework, the steps are often a type of "task" or
"job" object.

A simple pipeline could look something like the following:

.. code-block:: python

    ...

    def pipeline(file_path):
        data = load_from_source(file_path)  # STEP 1

        data = operation_one(data)          # STEP 2

        data = operation_two(data)          # STEP 3

        save_to_destination(data)           # STEP 4


You can simply add calls to :func:`validate()` *between* the
existing steps:

.. code-block:: python
    :emphasize-lines: 6,10-11,15

    ...

    def pipeline(file_path):
        data = load_from_source(file_path)  # STEP 1

        validate(data.columns, ['user_id', 'first_name', 'last_name'])

        data = operation_one(data)          # STEP 2

        validate(data.columns, ['user_id', 'full_name'])
        validate(data, (int, str))

        data = operation_two(data)          # STEP 3

        validate.unique(data['user_id'])

        save_to_destination(data)           # STEP 4


You could go further in a more sophisticated pipeline framework
and define tasks dedicated specifically to validation.


.. tip::

    When possible, it's best to call :func:`validate()` once for a batch of
    data rather than for individual elements. Doing this is more efficient
    and failures provide more context when fixing data issues or defining
    appropriate acceptances.

    .. code-block:: python
        :emphasize-lines: 3

        # Efficient:

        validate(data, int)

        for x in data:
            myfunc(x)

    .. code-block:: python
        :emphasize-lines: 4

        # Inefficient:

        for x in data:
            validate(x, int)
            myfunc(x)


Toggle Validation On/Off Using __debug__
========================================

Sometimes it's useful to perform comprehensive validation for
debugging purposes but disable validation for production runs.
You can use Python's :py:obj:`__debug__` constant to toggle
validation on or off as needed:

.. code-block:: python
    :emphasize-lines: 6-7,11-13,17-18

    ...

    def pipeline(file_path):
        data = load_from_source(file_path)  # STEP 1

        if __debug__:
            validate(data.columns, ['user_id', 'first_name', 'last_name'])

        data = operation_one(data)          # STEP 2

        if __debug__:
            validate(data.columns, ['user_id', 'full_name'])
            validate(data, (int, str))

        data = operation_two(data)          # STEP 3

        if __debug__:
            validate.unique(data['user_id'])

        save_to_destination(data)           # STEP 4


Validation On
-------------

In the example above, you can run the pipeline with validation
by running Python in *unoptimized* mode. In unoptimized mode,
``__debug__`` is True and ``assert`` statements are executed
normally. Unoptimized mode is the default mode when invoking
Python:

.. code-block:: console

    python simple_pipeline.py


Validation Off
--------------

To run the example above without validation, run Python in
*optimized* mode. In optimized mode, ``__debug__`` is False and
``assert`` statements are skipped. You can invoke optimized mode
using the :py:option:`-O` command line option:

.. code-block:: console

    python -O simple_pipeline.py


Validate a Sample from a Larger Data Set
========================================

Another option for dealing with large data sets is to validate
a small sample of the data. Doing this can provide some basic
sanity checking in a production pipeline but it could also allow
some invalid data to pass unnoticed. Users must decide if this
approach is appropriate for their specific use case.


DataFrame Example
-----------------

With Pandas, you can use the :meth:`DataFrame.sample()
<pandas.DataFrame.sample>` method to get a random sample
of items for validation:

.. code-block:: python
    :emphasize-lines: 10-12,16-17

    ...

    def pipeline(file_path):
        data = load_from_source(file_path)  # STEP 1

        validate(data.columns, ['user_id', 'first_name', 'last_name'])

        data = operation_one(data)          # STEP 2

        sample = data.sample(n=100)
        validate(sample.columns, ['user_id', 'full_name'])
        validate(sample, (int, str))

        data = operation_two(data)          # STEP 3

        sample = data.sample(n=100)
        validate.unique(sample['user_id'])

        save_to_destination(data)           # STEP 4


Iterator Example
----------------

Sometimes you will need to work with exhaustible iterators of
unknown size. It's possible for an iterator to yield more data
than you can load into memory at any one time. Using Python's
:py:mod:`itertools` module, you can fetch a sample of data for
validation and then reconstruct the iterator to continue with data
processing:

.. code-block:: python
    :emphasize-lines: 1,10-12,16-18

    import itertools

    ...

    def pipeline(file_path):
        iterator = load_from_source(file_path)  # STEP 1

        iterator = operation_one(iterator)      # STEP 2

        sample = list(itertools.islice(iterator, 100))
        validate(sample, (int, str))
        iterator = itertools.chain(sample, iterator)

        iterator = operation_two(iterator)      # STEP 3

        sample = list(itertools.islice(iterator, 100))
        validate.unique(item[0] for item in sample)
        iterator = itertools.chain(sample, iterator)

        save_to_destination(iterator)           # STEP 4


.. important::

    As previously noted, validating samples of a larger data set should
    be done with care. If the sample is not representative of the data
    set as a whole, some validations could fail even when the data is
    good and some validations could pass even when the data is bad.

    For example, the code above includes a call to :func:`validate.unique`
    but this validation is only checking the small sample---duplicates in
    the remaining data set could pass unnoticed. This may be acceptable
    for some situations but not for others.


..
    TODO: Add section on logging ValidationErrors instead of raising them.


Testing Pipeline Code Itself
============================

The pipeline validation discussed in this document is not a
replacement for proper testing of the pipeline's code base
itself. Pipeline code, should be treated with the same care
and attention as any other software project.

