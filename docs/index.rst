:tocdepth: 2

.. meta::
    :description: Datatest introduction and table of contents.
    :keywords: data cleaning, data quality, etl testing, data validation, data testing, data preparation, python, datatest
    :title: Datatest: Test driven data-wrangling and data validation.

.. module:: datatest
    :synopsis: Test driven data-wrangling and data validation.
.. moduleauthor:: Shawn Brown <sbrown@ncecservices.com>
.. sectionauthor:: Shawn Brown <sbrown@ncecservices.com>


########################################################
Datatest: Test driven data-wrangling and data validation
########################################################

Version |release|

Datatest helps to speed up and formalize data-wrangling and data
validation tasks. It was designed to work with poorly formatted
data by detecting and describing validation failures.

.. |comparison behavior| replace:: :ref:`comparison behavior <intro-smart-comparisons>`
.. |data handling| replace:: :ref:`data handling <intro-automatic-data-handling>`
.. |Difference objects| replace:: :ref:`Difference objects <intro-difference-objects>`
.. |Acceptance managers| replace:: :ref:`Acceptance managers <intro-acceptance-managers>`

* :ref:`Validate <intro-validation>` the format, type, set membership, and
  more from a variety of data sources including pandas ``DataFrames`` and
  ``Series``, NumPy ``ndarrays``, built-in data structures, etc.
* Smart |comparison behavior| applies the appropriate validation method for
  a given data requirement.
* Automatic |data handling| manages the validation of single elements,
  sequences, sets, dictionaries, and other containers of elements.
* |Difference objects| characterize the discrepancies and deviations
  between a dataset and its requirements.
* |Acceptance managers| distinguish between ideal criteria and acceptable
  differences.


**Test driven data-wrangling** is a process for taking data from a source
of unverified quality or format and producing a verified, well-formatted
dataset. It repurposes software testing practices for data preparation
and quality assurance projects. **Pipeline validation** monitors the status
and quality of data as it passes through a pipeline and identifies *where*
in a pipeline an error occurs.

See the project `README <https://pypi.org/project/datatest/>`_ file for
full details regarding supported versions, backward compatibility, and
more.


=================
Table of Contents
=================

.. toctree::
    :caption: Documentation
    :hidden:

    Home <self>


.. toctree::
    :maxdepth: 2

    intro/index
    how-to/index
    reference/index
    discussion/index

..
    OMIT UNFINISHED PAGES:
      tutorial/index

