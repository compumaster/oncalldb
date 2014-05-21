#
# Copyright 2014 Sinan Ussakli. All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be found in the LICENSE file.
#
from flask import _app_ctx_stack
import pprint
import psycopg2
import psycopg2.extras

import config

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
'''
    DATABASE
'''
def singleton(realdictcursor=False):
    top = _app_ctx_stack.top
    if not hasattr(top, 'posgresql'):
        conn = None
        connstr = "dbname='%s' user='%s' host='%s' password='%s'" % (config.DATABASE_NAME, config.DATABASE_USER, config.DATABASE_HOST, config.DATABASE_PWD)
        try:
            conn = psycopg2.connect(connstr)
        except Exception, e:
            pprint.pprint(e)
        top.posgresql = conn
    if realdictcursor:
        return top.posgresql.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        return top.posgresql.cursor(cursor_factory=psycopg2.extras.DictCursor)


def close_database(exception):
    top = _app_ctx_stack.top
    if hasattr(top, 'posgresql'):
        if top.posgresql:
            top.posgresql.close()

def execute(cur, query, args=()):
    cur.execute(query, args)

def commit(cur):
    cur.execute('COMMIT')

def query(cur, query, args=(), one=False):
    cur.execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv and len(rv) else None) if one else rv

def nonquery(cur, query, args=(), one=False):
    cur.execute(query, args)
