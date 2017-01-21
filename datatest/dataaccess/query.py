# -*- coding: utf-8 -*-
from __future__ import absolute_import
import collections
import functools
from ..utils.builtins import callable


def _validate_query_steps(query_steps):
    """Validate query steps--if invalid, raises TypeError else returns
    None. Call chain should be an iterable containing strings and
    2-tuples. In the case of 2-tuples, the first item must be an *args
    'tuple' and the second item must be a **kwds dict.
    """
    if isinstance(query_steps, str):
        raise TypeError("cannot be 'str'")

    try:
        iterable = iter(query_steps)
    except TypeError:
        raise TypeError('query_steps must be iterable')

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


def _get_step_repr(element):
    """Helper function returns repr for a single query step."""
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
            self._query_steps = ((args, kwds),)
        else:
            self._query_steps = tuple()

        self._initializer = None

    @classmethod
    def _from_parts(cls, query_steps=None, initializer=None):
        if query_steps:
            _validate_query_steps(query_steps)
            query_steps = tuple(query_steps)
        else:
            query_steps = tuple()

        new_cls = cls()
        new_cls._query_steps = query_steps
        new_cls._initializer = initializer
        return new_cls

    def __getattr__(self, name):
        query_steps = self._query_steps + (name,)
        new_query = self.__class__._from_parts(query_steps, self._initializer)
        return new_query

    def __call__(self, *args, **kwds):
        query_steps = self._query_steps + ((args, kwds),)
        new_query = self.__class__._from_parts(query_steps, self._initializer)
        return new_query

    def __repr__(self):
        class_name = self.__class__.__name__

        hex_id = hex(id(self))

        if self._initializer:
            initial_repr = '\n  ' + repr(self._initializer)
        else:
            initial_repr = ' <empty>'

        step_deque = collections.deque(self._query_steps)
        repr_list = []
        while step_deque:
            one_step = step_deque.popleft()
            one_repr = _get_step_repr(one_step)
            if (isinstance(one_step, str) and
                    step_deque and isinstance(step_deque[0], tuple)):
                arguments = step_deque.popleft()
                one_repr = one_repr + _get_step_repr(arguments)
            repr_list.append(one_repr)

        if repr_list:
            #steps_repr = [f'  {x}' for x in  repr_list]
            steps_repr = ['  {0}'.format(x) for x in  repr_list]
            steps_repr = '\n' + '\n'.join(steps_repr)
        else:
            steps_repr = ' <empty>'

        return ('<{0} object at {1}>\n'
                'query_steps:{2}\n'
                'initializer:{3}').format(class_name, hex_id, steps_repr, initial_repr)

    @staticmethod
    def _reduce(query_steps, initializer):
        """."""
        def function(obj, val):
            if isinstance(val, str):
                return getattr(obj, val)
            args, kwds = val  # Unpack tuple.
            return obj(*args, **kwds)

        return functools.reduce(function, query_steps, initializer)

    def _eval(self, initializer=None):
        initializer = initializer or self._initializer
        if initializer is None:
            raise ValueError('must provide initializer, none found')

        query_steps = self._query_steps
        return self._reduce(query_steps, initializer)


class _DataQuery(BaseQuery):
    @staticmethod
    def _optimize(query_steps):
        """Return optimized query_steps for faster performance with
        DataSource object (if possible). If query_steps cannot be
        optimized, it will be returned without changes.
        """
        try:
            meth_one = query_steps[0]
            args_one = query_steps[1]
            meth_two = query_steps[2]
            args_two = query_steps[3]
        except IndexError:
            return query_steps  # <- EXIT!

        is_select = (meth_one == '_select'
                     and isinstance(args_one, tuple))
        is_aggregate = (meth_two in ('sum', 'avg', 'min', 'max')  # TODO: Add count.
                        and args_two == ((), {}))

        if is_select and is_aggregate:
            args, kwds = args_one
            args = (meth_two.upper(),) + args
            query_steps = ('_select_aggregate', (args, kwds)) + query_steps[4:]
            return query_steps  # <- EXIT!

        return query_steps

    def eval(self, initializer=None, **kwds):
        """
        eval(initializer=None, *, lazy=False, optimize=True)

        Evaluate query and return its result.

        Use ``lazy=True`` to evaluate the query but leave the result
        in its raw, iterator form. By default, results are eagerly
        evaluated and loaded into memory.

        Use ``optimize=False`` to turn-off query optimization.
        """
        initializer = initializer or self._initializer
        if initializer is None:
            raise ValueError('must provide initializer, none found')

        lazy = kwds.pop('lazy', False)         # Emulate keyword-only
        optimize = kwds.pop('optimize', True)  # behavior for 2.7 and
        if kwds:                               # 2.6 compatibility.
            key, _ = kwds.popitem()
            raise TypeError('got an unexpected keyword '
                            'argument {0!r}'.format(key))

        query_steps = self._query_steps
        if optimize:
            query_steps = self._optimize(query_steps)

        result = self._reduce(query_steps, initializer)

        if not lazy:
            try:
                return result.eval()  # <- EXIT!
            except AttributeError:
                pass
        return result
