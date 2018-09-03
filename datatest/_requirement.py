# -*- coding: utf-8 -*-
from ._compatibility.builtins import *
from ._compatibility import abc
from ._utils import iterpeek


class Requirement(abc.ABC):
    @property
    @abc.abstractmethod
    def msg(self):
        raise NotImplementedError

    @abc.abstractmethod
    def filterfalse(self, iterable):
        raise NotImplementedError

    def __call__(self, iterable):
        diffs = self.filterfalse(iterable)
        first_element, diffs = iterpeek(diffs)
        if first_element:
            return diffs
        return None
