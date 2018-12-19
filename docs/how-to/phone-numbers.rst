
.. module:: datatest

.. meta::
    :description: How to assert telephone number formats.
    :keywords: datatest, phone format, validate phone number


#############################
How to Validate Phone Numbers
#############################

To check that phone numbers are well-formed, you can use a regular
expression.

The following example gives a regular expression for North American
style phone numbers with various separator characters (e.g.,
``(123) 456-7890``, ``123-456-7890``, etc.):

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 9,11

            import re
            import datatest


            def test_phone_numbers():

                data = ['(555) 123-1234', '555-123-1234', '555.123.1234']

                phone_number = re.compile('^(1\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$')

                datatest.validate(data, phone_number)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 11,13

            import re
            import datatest


            class MyTest(datatest.DataTestCase):

                def test_phone_numbers(self):

                    data = ['(555) 123-1234', '555-123-1234', '555.123.1234']

                    phone_number = re.compile('^(1\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$')

                    self.assertValid(data, phone_number)


A Looser But More Robust Test
=============================

For a looser test that will work in more cases, you can use a function
to remove all non-digit characters from the string and check the remaining
length:

.. code-block:: python

    import datatest


    def phone_number(value):
        """should be North American phone number"""
        digits_only = ''.join(x for x in value if x.isdigit())
        length = len(digits_only)
        return length == 10 or (length == 11 and digits_only[0] == '1')

    ...

The function above is used the same way the regular expression was
used in the first example---simply pass it as the *requirement*
when calling the validation function.
