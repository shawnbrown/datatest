
.. module:: datatest

.. meta::
    :description: Errors, differences, and allowances.
    :keywords: datatest, difference, error, allowance


####################
Error and Difference
####################


***************
ValidationError
***************

.. autoexception:: ValidationError

    .. autoattribute:: message

    .. autoattribute:: differences

    .. autoattribute:: args


***********
Differences
***********

.. autoclass:: Missing
    :members:


.. autoclass:: Extra
    :members:


.. autoclass:: Invalid


.. autoclass:: Deviation

    .. autoattribute:: deviation

    .. autoattribute:: percent_deviation

    .. autoattribute:: expected
