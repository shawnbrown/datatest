
Release Checklist
=================

1. Make sure correct version number is set in the following files
   (remove the ".devN" suffix):

       datatest/__init__.py
       docs/conf.py

2. Make sure the description argument in setup.py matches the project
   description on GitHub.

3. Check that *packages* argument of setup() is correct. Check with:

       >>> import setuptools
       >>> sorted(setuptools.find_packages('.', exclude=['tests']))

4. Make sure `__past__` sub-package includes a stub module for the
   current API version.

5. Update README.rst (including "Backward Compatibility" section).

6. Commit and push final changes to upstream repository:

       Prepare version info, CHANGELOG, and README for version N.N.N release.

7. Perform final checks to make sure there are no CI test failures.

8. Make sure the packaging tools are up-to-date:

       pip install -U twine wheel setuptools

9. Remove all existing files in the `dist/` folder.

10. Build new distributions:

        python setup.py sdist bdist_wheel

11. Upload source and wheel distributions to PyPI:

        twine upload dist/*

12. Double check PyPI project page and test installation from PyPI.

13. Add version tag to upstream repository (also used by readthedocs.org).

14. Iterate version number in repository indicating that it is a development
    version (e.g., N.N.N.dev1) so that "latest" docs aren't confused with the
    just-published "stable" docs:

	    datatest/__init__.py
        docs/conf.py

    Commit these changes with a comment like the one below:

        Iterate version number to differentiate development version
        from latest release.

15. Make sure the documentation reflects the new versions:

    * https://datatest.readthedocs.io/ (stable)
    * https://datatest.readthedocs.io/en/latest/ (latest)

16. Publish update announcement to relevant mailing lists:

    * python-announce-list@python.org
    * testing-in-python@lists.idyll.org
