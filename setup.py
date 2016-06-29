#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import ast
import os.path

try:
    from setuptools import setup
    from setuptools import Command
except ImportError:
    from distutils.core import setup
    from distutils.core import Command


class TestCommand(Command):
    """Implement 'setup.py test' command."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # Print "skipping" notice if missing optional packages.
        missing_optionals = self._get_missing_optionals()
        if missing_optionals:
            msg = 'optionals not installed: {0}\nskipping some tests'
            print(msg.format(', '.join(missing_optionals)))

        # Run tests.
        import subprocess, sys
        if sys.version_info[:2] in [(2, 6), (3, 1)]:
            args = [sys.executable, '-B', 'tests/discover.py']
        else:
            args = [sys.executable, '-B', '-m', 'unittest', 'discover']
        exit(subprocess.call(args))

    def _get_missing_optionals(self):
        # Returns a list of missing optional packages.
        optional_packages = [
            'pandas',
            'xlrd',  # <- support for MS Excel files
        ]
        missing_optionals = []
        for package in optional_packages:
            try:
                __import__(package)
            except ImportError:
                missing_optionals.append(package)
        return missing_optionals


class RestrictedCommand(Command):
    """Dummy command to restrict setup.py actions."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        raise Exception('This command is currently restricted.')


def get_version(filepath):
    """Return value of file's __version__ attribute."""
    fullpath = os.path.join(os.path.dirname(__file__), filepath)
    with open(fullpath) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith('__version__'):
                return ast.parse(line).body[0].value.s
    raise Exception('Unable to find __version__ attribute.')


if __name__ == '__main__':
    with open('README.rst') as file:
        long_description = file.read()

    setup(
        # Required meta-data:
        name='datatest',
        version=get_version('datatest/__init__.py'),
        url='https://pypi.python.org/pypi/datatest',
        packages=[
            'datatest',
            'datatest.sources',
            'datatest.utils',
            'datatest.__past__',
        ],
        # Additional fields:
        description='Testing tools for data preparation.',
        long_description=long_description,
        author='Shawn Brown',
        classifiers  = [
            'Topic :: Software Development :: Quality Assurance',
            'Topic :: Software Development :: Testing',
            'License :: OSI Approved :: Apache Software License',
            'Development Status :: 4 - Beta',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.1',
            'Programming Language :: Python :: 3.2',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
        ],
        cmdclass={
            'test': TestCommand,
            # Restrict setup commands (use twine instead):
            'register': RestrictedCommand,  # Use: twine register dist/*
            'upload': RestrictedCommand,    # Use: twine upload dist/*
            'upload_docs': RestrictedCommand,
        },
    )

# Release Checklist
# -----------------
# Set version number in:
#   datatest/__init__.py
#   docs/config.py
# Commit and push version change to upstream repository.
# Add version tag to upstream repository.
# Remove all existing files in the dist/ folder.
# Build new distributions:
#   python setup.py sdist bdist_wheel
# Register source distribution with PyPI:
#   twine register dist/datatest.X.Y.Z.tar.gz
# Upload source and wheel distributions to PyPI:
#   twine upload dist/*
