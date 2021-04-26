
Release Checklist
=================

#. Make sure correct version number is set in the following files
   (remove the ".devN" suffix):

   * ``datatest/__init__.py``
   * ``docs/conf.py``

#. Make sure the description argument in setup.py matches the project
   description on GitHub.

#. Check that *packages* argument of ``setup()`` is correct. Check with:

   .. code-block:: python

        >>> import setuptools
        >>> sorted(setuptools.find_packages('.', exclude=['tests']))

#. Make sure ``__past__`` sub-package includes a stub module for the
   current API version.

#. Update ``README.rst`` (including "Backward Compatibility" section).

#. Commit and push final changes to upstream repository:

        Prepare version info, CHANGELOG, and README for version N.N.N release.

#. Perform final checks to make sure there are no CI test failures.

#. Make sure the packaging tools are up-to-date:

   .. code-block:: console

        pip install -U twine wheel setuptools check-manifest

#. Check the manifest against the project's root folder:

   .. code-block:: console

        check-manifest .

#. Remove all existing files in the ``dist/`` folder.

#. Build new distributions:

   .. code-block:: console

        python setup.py sdist bdist_wheel

#. Upload source and wheel distributions to PyPI:

   .. code-block:: console

        twine upload dist/*

#. Double check PyPI project page and test installation from PyPI.

#. Add version tag to upstream repository (also used by readthedocs.org).

#. Iterate version number in repository indicating that it is a development
   version (e.g., N.N.N.dev1) so that "latest" docs aren't confused with the
   just-published "stable" docs:

   * ``datatest/__init__.py``
   * ``docs/conf.py``

   Commit these changes with a comment like the one below:

        Iterate version number to differentiate development version
        from latest release.

#. Make sure the documentation reflects the new versions:

   * https://datatest.readthedocs.io/ (stable)
   * https://datatest.readthedocs.io/en/latest/ (latest)

#. Publish update announcement to relevant mailing lists:

   * python-announce-list@python.org
   * testing-in-python@lists.idyll.org
