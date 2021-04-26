
Release Checklist
=================

#. Make sure correct version number is set in the following files
   (remove the ".devN" suffix):

   * ``datatest/__init__.py``
   * ``docs/conf.py``

#. Make sure the *description* argument in ``setup.py`` matches the project
   description on GitHub (in the "About" section).

#. In the call to ``setup()``, check the versions defined by the
   *python_requires* argument (see the "Version specifiers" section of
   PEP-440 for details).

#. In the call to ``setup()``, check the trove classifiers in the
   *classifiers* argument (see https://pypi.org/classifiers/ for values).

#. Check that *packages* argument of ``setup()`` is correct. Check that the
   value matches what ``setuptools.find_packages()`` returns:

   .. code-block:: python

        >>> import setuptools
        >>> sorted(setuptools.find_packages('.', exclude=['tests']))

   Defining this list explicitly (rather than using ``find_packages()``
   directly in ``setup.py`` file) is needed when installing on systems
   where ``setuptools`` is not available.

#. Make sure ``__past__`` sub-package includes a stub module for the
   current API version.

#. Update ``README.rst`` (including "Backward Compatibility" section).

#. Make final edits to ``CHANGELOG`` (doublecheck release date and version).

#. Commit and push final changes to upstream repository:

        Prepare version info, README, and CHANGELOG for version N.N.N release.

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

#. Upload distributions to TestPyPI:

   .. code-block:: console

        twine upload --repository testpypi dist/*

#. View the package's web page on TestPyPI and verify that the information
   is correct for the "Project links" and "Meta" sections:

   * https://test.pypi.org/project/datatest

   If you are testing a pre-release version, make sure to use the URL returned
   by twine in the previous step (the default URL shows the latest *stable*
   version).

#. Test the installation process from TestPyPI:

   .. code-block:: console

        python -m pip install --index-url https://test.pypi.org/simple/ datatest

   If you're testing a pre-release version, make sure to use the "pip install"
   command listed at the top of the project's TestPyPI page.

#. Upload source and wheel distributions to PyPI:

   .. code-block:: console

        twine upload dist/*

#. Double check PyPI project page and test installation from PyPI:

   .. code-block:: console

        python -m pip install datatest

#. Add version tag to upstream repository (also used by readthedocs.org).

#. Iterate the version number in the development repository to the next
   anticipated release and add a "dev" suffix (e.g., N.N.N.dev1). This
   version number should conform to the "Version scheme" section of PEP-440.
   Make sure these changes are reflected in the following files:

   * ``datatest/__init__.py``
   * ``docs/conf.py``

   Commit these changes with a comment like the one below:

        Iterate version number to the next anticipated release.

   This is done so that installations made directly from the development
   repository and the "latest" docs are not confused with the just-published
   "stable" versions.

#. Make sure the documentation reflects the new versions:

   * https://datatest.readthedocs.io/ (stable)
   * https://datatest.readthedocs.io/en/latest/ (latest)

   If the documentation was not automatically updated, you may need to
   login to https://readthedocs.org/ and start the build process manually.

#. Publish update announcement to relevant mailing lists:

   * python-announce-list@python.org
   * testing-in-python@lists.idyll.org
