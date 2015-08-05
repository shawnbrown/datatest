#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ast
from distutils.core import setup
from distutils.core import Command


class RestrictedCommand(Command):
    """Dummy command to restrict setup.py actions."""
    user_options = []
    def initialize_options(self): pass
    def finalize_options(self): pass
    def run(self): raise Exception('This command is currently restricted.')


def get_version(filepath):
    """Return value of file's __version__ attribute."""
    with open(filepath, newline='') as fh:
        for line in fh:
            line = line.strip()
            if line.startswith('__version__'):
                version = ast.parse(line).body[0].value.s
                break
    assert 'version' in locals(), 'Unable to find __version__ attribute.'
    return version


if __name__ == '__main__':
    setup(name='datatest',
          version=get_version('datatest/__init__.py'),
          description='Data testing tools for Python.',
          author='Shawn Brown',
          #author_email='',
          #url='',
          #packages=['distutils', 'distutils.command'],
          classifiers  = ['Development Status :: 3 - Alpha',
                          #'License :: OSI Approved :: Apache Software License',
                          'Topic :: Software Development :: Quality Assurance',
                          'Topic :: Software Development :: Testing',
                          'Programming Language :: Python :: 2',
                          'Programming Language :: Python :: 2.6',
                          'Programming Language :: Python :: 2.7',
                          'Programming Language :: Python :: 3',
                          'Programming Language :: Python :: 3.1',
                          'Programming Language :: Python :: 3.2',
                          'Programming Language :: Python :: 3.3',
                          'Programming Language :: Python :: 3.4',
                         ],
          # Restrict unintended upload of private code to public PyPI:
          cmdclass={'register':    RestrictedCommand,
                    'upload':      RestrictedCommand,
                    'upload_docs': RestrictedCommand},
         )
