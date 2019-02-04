#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sphinx Extension: autodoc_classinstance (written by Shawn Brown)."""
from sphinx.domains.python import PyClasslike
from sphinx.ext.autodoc import ClassDocumenter
from sphinx.ext.autodoc import ClassLevelDocumenter
from sphinx.ext.autodoc import MethodDocumenter
from sphinx.util.inspect import isclassmethod
from sphinx.util.inspect import isstaticmethod
from sphinx.util.inspect import Signature


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
        # type: (Any, str, bool, Any) -> bool
        return not isinstance(member, type)

    def import_object(self):
        # type: () -> Any
        ret = super().import_object()
        self.doc_as_attr = False  # never document as a data/attribute
        return ret

    def format_args(self):
        # type: () -> str
        # for instances, the relevant signature is the __call__ method's
        callmeth = self.get_attr(self.object, '__call__', None)
        if callmeth:
            return Signature(callmeth, bound_method=True, has_retval=True).format_args()
        return None


class AlternateMethodDocumenter(MethodDocumenter):
    """
    Alternative specialized Documenter subclass for methods (normal,
    static and class) of classes and class isntances.
    """
    objtype = 'method'

    def import_object(self):
        # type: () -> Any
        ret = ClassLevelDocumenter.import_object(self)
        if not ret:
            return ret

        # get parent's class
        parent_cls = self.parent
        if not isinstance(parent_cls, type):
            parent_cls = parent_cls.__class__  # if instance, get its class

        # to distinguish classmethod/staticmethod
        obj = parent_cls.__dict__.get(self.object_name)
        if obj is None:
            obj = self.object

        if isclassmethod(obj):
            self.directivetype = 'classmethod'
            # document class and static members before ordinary ones
            self.member_order = self.member_order - 1
        elif isstaticmethod(obj, cls=parent_cls, name=self.object_name):
            self.directivetype = 'staticmethod'
            # document class and static members before ordinary ones
            self.member_order = self.member_order - 1
        else:
            self.directivetype = 'method'
        return ret


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
