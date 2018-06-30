:tocdepth: 2

.. meta::
    :description: Table of Contents for Datatest.
    :keywords:
    :title: Index

.. module:: datatest
    :synopsis: Testing tools for data validation and analysis.
.. moduleauthor:: Shawn Brown <sbrown@ncecservices.com>
.. sectionauthor:: Shawn Brown <sbrown@ncecservices.com>


########################################################
Datatest: Testing tools for data validation and analysis
########################################################

Version |release|

.. include:: ../README.rst
    :start-after: start-inclusion-marker-description
    :end-before: end-inclusion-marker-description

See the project's `README <https://pypi.org/project/datatest/>`_
file for full details regarding supported versions, backward
compatibility, and more.


.. toctree::
    :caption: Documentation
    :maxdepth: 2

    tutorial/index.rst
    how-to/index.rst
    reference/index.rst
    Discussion <discussion/data-wrangling.rst>


.. note::
    This documentation is aimed at newer versions of Python and
    uses some of the following features:

    * :py:class:`set` literals: ``{1, 2, 3}``
    * :py:data:`Ellipsis` literals: ``...`` (for wildcard :ref:`predicate-docs`)
    * the :py:mod:`statistics` module
    * f-strings (formatted string literals, see :pep:`498`)

    If you are using an older version of Python, you may need to
    convert some examples into older syntax before running them.
