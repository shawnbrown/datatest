#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import ast
import optparse
import os
import subprocess
import sys
import warnings

try:
    from setuptools import setup
    from setuptools import Command
except ImportError:
    from distutils.core import setup
    from distutils.core import Command


WORKING_DIR = os.path.dirname(os.path.abspath(__file__))

class TestCommand(Command):
    """Implement 'setup.py test' command."""
    user_options = [
        ('verbose', 'v', 'Verbose testing output'),
        ('failfast', 'f', 'Stop testing on first fail or error'),
    ]

    boolean_options = ['verbose', 'failfast']

    description = 'run test suite'

    def initialize_options(self):
        self.verbose = None
        self.failfast = None

    def finalize_options(self):
        cmd_args = sys.argv                           # Since "verbose" is
        cmd_args = cmd_args[cmd_args.index('test'):]  # also a global option
                                                      # for setup.py, we need
        parser = optparse.OptionParser()              # to parse only args
        parser.add_option(                            # after the command.
            '--verbose', '-v', action='store_true', default=False)
        opts, _ = parser.parse_args(cmd_args)
        self.verbose = opts.verbose

        if self.failfast is None:
            self.failfast = False
        elif sys.version_info[:2] in [(2, 6), (3, 1)]:
            msg = 'failfast option not supported in this version of Python'
            warnings.warn(msg)
            self.failfast = False

    def run(self):
        # Print "skipping" notice if missing optional packages.
        missing_optionals = self._get_missing_optionals()
        if missing_optionals:
            msg = 'optionals not installed: {0}\nskipping some tests'
            print(msg.format(', '.join(missing_optionals)))

        # Prepare test command.
        if sys.version_info[:2] in [(2, 6), (3, 1)]:
            args = [sys.executable, '-B', '-O', 'tests/discover.py']
        else:
            args = [sys.executable, '-B', '-O', '-m', 'unittest', 'discover']

        if self.verbose:
            args.append('--verbose')

        if self.failfast:
            args.append('--failfast')

        # Run tests.
        exit(subprocess.call(args))

    def _get_missing_optionals(self):
        # Returns a list of missing optional packages.
        optional_packages = [
            'dbfread',
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
    fullpath = os.path.join(WORKING_DIR, filepath)
    with open(fullpath) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith('__version__'):
                return ast.parse(line).body[0].value.s
    raise Exception('Unable to find __version__ attribute.')


if __name__ == '__main__':
    original_dir = os.path.abspath(os.getcwd())
    try:
        os.chdir(WORKING_DIR)
        with open('README.rst') as file:
            long_description = file.read()

        setup(
            # Required meta-data:
            name='datatest',
            version=get_version('datatest/__init__.py'),
            url='https://pypi.org/project/datatest/',
            packages=[
                'datatest',
                'datatest._compatibility',
                'datatest._compatibility.collections',
                'datatest._load',
                'datatest._query',
                'datatest.__past__',
            ],
            # Additional fields:
            description='Test driven data-wrangling and data validation.',
            long_description=long_description,
            author='Shawn Brown',
            license='Apache 2.0',
            classifiers  = [
                'Topic :: Software Development :: Quality Assurance',
                'Topic :: Software Development :: Testing',
                'License :: OSI Approved :: Apache Software License',
                'Development Status :: 4 - Beta',
                'Framework :: Pytest',
                'Programming Language :: Python :: 2',
                'Programming Language :: Python :: 2.6',
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3',
                'Programming Language :: Python :: 3.1',
                'Programming Language :: Python :: 3.2',
                'Programming Language :: Python :: 3.3',
                'Programming Language :: Python :: 3.4',
                'Programming Language :: Python :: 3.5',
                'Programming Language :: Python :: 3.6',
                'Programming Language :: Python :: 3.7',
                'Programming Language :: Python :: 3.8',
                'Programming Language :: Python :: Implementation :: CPython',
                'Programming Language :: Python :: Implementation :: PyPy',
            ],
            entry_points={
                'pytest11': [
                    'datatest = datatest._pytest_plugin',
                ],
            },
            cmdclass={
                'test': TestCommand,
                # Restrict setup commands (use twine instead):
                'register': RestrictedCommand,  # Use: twine register dist/*
                'upload': RestrictedCommand,    # Use: twine upload dist/*
                'upload_docs': RestrictedCommand,
            },
        )
    finally:
        os.chdir(original_dir)
