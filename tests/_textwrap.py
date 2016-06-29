"""compatibility layer for textwrap (Python standard library)"""
from __future__ import absolute_import
from textwrap import *


try:
    indent
except NameError:
    def indent(text, prefix, predicate=None):
        if predicate is None:
            def predicate(line):
                return line.strip()

        def prefixed_lines():
            for line in text.splitlines(True):
                yield (prefix + line if predicate(line) else line)
        return ''.join(prefixed_lines())
