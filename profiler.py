# -*- coding: utf-8 -*-

import cProfile
from functools import wraps

# profiling decorator
def profiler():

    def _profiler(f):
        @wraps(f)
        def __profiler(*rgs, **kwargs):
            pr = cProfile.Profile()
            pr.enable()
            result = f(*rgs, **kwargs)
            pr.disable()

            dump_file = '%s.profile' % f.__name__
            pr.dump_stats(dump_file)
            return result

        return __profiler

    return _profiler
