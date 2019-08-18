# -*- coding: utf-8 -*-
import pstats
import sys

pstats.Stats(sys.argv[1]).strip_dirs().sort_stats('cumulative').print_stats()