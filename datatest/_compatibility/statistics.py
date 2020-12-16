from __future__ import absolute_import
from __future__ import division

try:
    from statistics import *
except ImportError:

    class StatisticsError(ValueError):
        pass


    def median(data):
        data = sorted(data)
        n = len(data)
        if n == 0:
            raise StatisticsError('no median for empty data')
        if n % 2 == 1:
            return data[n // 2]
        else:
            i = n // 2
            return (data[i - 1] + data[i]) / 2
