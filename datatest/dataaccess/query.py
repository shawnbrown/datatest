# -*- coding: utf-8 -*-
from __future__ import absolute_import
import collections
import functools
from ..utils.builtins import callable


def _validate_call_chain(call_chain):
    """Validate call chain--if invalid, raises TypeError else returns
    None. Call chain should be an iterable containing strings and
    2-tuples. In the case of 2-tuples, the first item must be an *args
    'tuple' and the second item must be a **kwds dict.
    """
    if isinstance(call_chain, str):
        raise TypeError("cannot be 'str'")

    try:
        iterable = iter(call_chain)
    except TypeError:
        raise TypeError('call_chain must be iterable')

    for item in iterable:
        if isinstance(item, str):
            continue  # Skip to next item.

        if not isinstance(item, tuple):
            err_msg = 'item must be string or 2-tuple, found {0}'
            err_obj = type(item).__name__
        elif len(item) != 2:
            err_msg = 'expected string or 2-tuple, found {0}-tuple'
            err_obj = len(item)
        elif not isinstance(item[0], tuple):
            err_msg = "first item must be *args 'tuple', found {0}"
            err_obj = type(item[0]).__name__
        elif not isinstance(item[1], dict):
            err_msg = "second item must be **kwds 'dict', found {0}"
            err_obj = type(item[1]).__name__
        else:
            err_msg = None
            err_obj = None

        if err_msg:
            raise TypeError(err_msg.format(repr(err_obj)))


def _get_element_repr(element):
    """Helper function returns repr for a single call chain element."""
    if isinstance(element, str):
        return element  # <- EXIT!

    args, kwds = element

    def _callable_name_or_repr(x):  # <- Helper function for
        if callable(x):             #    the helper function!
            try:
                return x.__name__
            except NameError:
                pass
        return repr(x)

    args_repr = ', '.join(_callable_name_or_repr(x) for x in args)

    kwds_repr = kwds.items()
    kwds_repr = [(k, _callable_name_or_repr(v)) for k, v in kwds_repr]
    kwds_repr = ['{0}={1}'.format(k, v) for k, v in kwds_repr]
    kwds_repr = ', '.join(kwds_repr)
    if args_repr and kwds_repr:
        kwds_repr = ', ' + kwds_repr

    return '({0}{1})'.format(args_repr, kwds_repr)


class BaseQuery(object):
    def __init__(self, *args, **kwds):
        if args or kwds:
            self._call_chain = ((args, kwds),)
        else:
            self._call_chain = tuple()

        self._data_source = None

    @classmethod
    def _from_parts(cls, data_source=None, call_chain=None):
        if call_chain:
            _validate_call_chain(call_chain)
            call_chain = tuple(call_chain)
        else:
            call_chain = tuple()

        new_cls = cls()
        new_cls._data_source = data_source
        new_cls._call_chain = call_chain
        return new_cls

    def __getattr__(self, name):
        call_chain = self._call_chain + (name,)
        new_query = self.__class__._from_parts(self._data_source, call_chain)
        return new_query

    def __call__(self, *args, **kwds):
        call_chain = self._call_chain + ((args, kwds),)
        new_query = self.__class__._from_parts(self._data_source, call_chain)
        return new_query

    def __repr__(self):
        class_name = self.__class__.__name__
        if self._data_source:
            source_repr = repr(self._data_source)
        else:
            source_repr = '<empty>'

        call_chain = collections.deque(self._call_chain)
        query_steps = []
        while call_chain:
            element = call_chain.popleft()
            element_repr = _get_element_repr(element)
            if (isinstance(element, str) and
                    call_chain and isinstance(call_chain[0], tuple)):
                arguments = call_chain.popleft()
                element_repr = element_repr + _get_element_repr(arguments)
            query_steps.append(element_repr)

        if query_steps:
            #fn = lambda indent, step: f'{"  " * indent}| {step}'
            fn = lambda indent, step: '{0}| {1}'.format(('  ' * indent), step)
            query_repr = [fn(i, s) for i, s in enumerate(query_steps)]
            query_repr = '\n' + '\n'.join(query_repr)
        else:
            query_repr = ' <empty>'

        return ('<class \'datatest.{0}\'>\n'
                'Preset Source: {1}\n'
                'Query Steps:{2}').format(class_name, source_repr, query_repr)

    def _eval(self, data_source=None, call_chain=None):
        data_source = data_source or self._data_source
        if data_source == None:
            raise ValueError('must provide data_source, no preset found')

        if not call_chain:
            call_chain = self._call_chain

        def function(obj, val):
            if isinstance(val, str):
                return getattr(obj, val)
            args, kwds = val  # Unpack tuple.
            return obj(*args, **kwds)

        return functools.reduce(function, call_chain, data_source)


class _DataQuery(BaseQuery):
    @staticmethod
    def _optimize(call_chain):
        """Return optimized call_chain for faster performance with
        DataSource object (if possible). If call_chain cannot be
        optimized, it will be returned without changes.
        """
        try:
            meth_one = call_chain[0]
            args_one = call_chain[1]
            meth_two = call_chain[2]
            args_two = call_chain[3]
        except IndexError:
            return call_chain  # <- EXIT!

        is_select = (meth_one == '_select'
                     and isinstance(args_one, tuple))
        is_aggregate = (meth_two in ('sum', 'avg', 'min', 'max')  # TODO: Add count.
                        and args_two == ((), {}))

        if is_select and is_aggregate:
            args, kwds = args_one
            args = (meth_two.upper(),) + args
            call_chain = ('_select_aggregate', (args, kwds)) + call_chain[4:]
            return call_chain  # <- EXIT!

        return call_chain

    def eval(self, lazy=False, optimize=True):
        """Evaluate query and return its result.

        Use ``lazy=True`` to evaluate the query but leave the result
        in its raw, iterator form. By default, results are eagerly
        evaluated and loaded into memory.

        Use ``optimize=False`` to turn-off query optimization.
        """
        call_chain = self._call_chain
        if optimize:
            call_chain = self._optimize(call_chain)

        result = self._eval(call_chain=call_chain)  # <- Evaluate!

        if not lazy:
            try:
                return result.eval()  # <- EXIT!
            except AttributeError:
                pass
        return result
