#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sphinx Extension: autodoc_classinstance (written by Shawn Brown)."""
from sphinx.domains.python import PyClasslike
from sphinx.ext.autodoc import ClassDocumenter
from sphinx.ext.autodoc import MethodDocumenter
from sphinx.util import inspect


try:
    iscoroutinefunction = inspect.iscoroutinefunction  # New in Sphinx v2.1.0
except AttributeError:
    iscoroutinefunction = lambda x: False  # Dummy lambda if not supported.


class PyClassInstance(PyClasslike):
    """
    Description of a class-instance object.
    """
    def get_signature_prefix(self, sig):
        return ''  # Omit "class" prefix for instances.


class ClassInstanceDocumenter(ClassDocumenter):
    """
    Specialized Documenter subclass for class instances.
    """
    objtype = 'classinstance'

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return not isinstance(member, type)

    def import_object(self):
        ret = super().import_object()
        self.doc_as_attr = False  # never document as a data/attribute
        return ret

    def format_args(self):
        # for instances, the relevant signature is the __call__ method's
        callmeth = self.get_attr(self.object, '__call__', None)
        if callmeth:
            sig = inspect.Signature(callmeth, bound_method=True, has_retval=True)
            return sig.format_args()
        return None


class AlternateMethodDocumenter(MethodDocumenter):
    """
    Alternative documenter for methods of classes and class instances.
    """
    def add_directive_header(self, sig):
        if isinstance(self.parent, type):
            # If parent is a class definition, then add header as normal.
            super(AlternateMethodDocumenter, self).add_directive_header(sig)
        else:
            # When parent is an instance, then add a special header
            # (calls superclass' superclass method).
            super(MethodDocumenter, self).add_directive_header(sig)

            # Tag async methods but do not tag abstract, class, or
            # static methods.
            parentclass = self.parent.__class__
            obj = parentclass.__dict__.get(self.object_name, self.object)
            if iscoroutinefunction(obj):
                sourcename = self.get_sourcename()
                self.add_line('   :async:', sourcename)


def setup(app):
    app.add_directive('classinstance', PyClassInstance)
    app.add_directive('py:classinstance', PyClassInstance)
    app.add_autodocumenter(ClassInstanceDocumenter)

    # If sphinx.ext.autosummary is used, it will override the
    # existing autodocumenters on the 'builder-inited' event.
    # Adding AlternateMethodDocumenter after this event makes
    # sure it isn't overridden.
    def add_method_documenter(app, env, docnames):
        app.add_autodocumenter(AlternateMethodDocumenter)
    app.connect('env-before-read-docs', add_method_documenter)
