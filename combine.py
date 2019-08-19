# -*- coding: utf-8 -*-
'''
For all the games, build the discard pile for each player for each hand,
and store in the database
'''

# 3,679,536 kb ; 15331 entries for 201801 ; 21s
# 745,128 kb ; 3066 entries ; 4.1s
# 125,064 kb; 473 entries ; 0.76s

import bz2
import sqlite3
from lxml import etree

from reshaper import Reshaper

db_dir = 'D:/azps/tenhou/logs'

for year in range(2019, 2020): # 2011

    with sqlite3.connect('%s/%d.db' % (db_dir, year,)) as conn:
        cursor = conn.cursor()
        for month in range(1, 2): # 13
            this_date = '%d%02d' % (year, month,)
            cursor.execute(
                "SELECT log_id, log_content FROM logs WHERE is_hirosima=0 AND is_tonpusen=0 AND log_id LIKE(?) LIMIT 1",
                ('%s%%' % this_date,))

            parent = etree.XML('<MONTH date="%s"/>' % this_date)
            while True:
                log = cursor.fetchone()
                if log is None:
                    break
                content = bz2.decompress(log[1])
                game = etree.XML(content, etree.XMLParser(recover=True))
                parent.append(Reshaper(game, log[0]).process())

            with open(db_dir + '/' + this_date + '.bz2', 'wb') as f:
                f.write(bz2.compress(etree.tostring(parent, encoding='utf-8', pretty_print=False)))

with open(db_dir + '/xml.txt', 'wb') as f:
    f.write(content)
