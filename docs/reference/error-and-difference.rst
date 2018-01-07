
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

.. autoclass:: BaseDifference

    .. autoattribute:: args


.. autoclass:: Missing


.. autoclass:: Extra


.. autoclass:: Invalid

    .. autoinstanceattribute:: datatest.difference.Invalid.invalid
       :annotation:

    .. autoinstanceattribute:: datatest.difference.Invalid.expected
       :annotation:


.. autoclass:: Deviation

    .. autoinstanceattribute:: datatest.difference.Deviation.deviation
       :annotation:

    .. autoinstanceattribute:: datatest.difference.Deviation.expected
       :annotation:
