#
# Copyright 2014 Sinan Ussakli. All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be found in the LICENSE file.
#
from functools import wraps
from flask import request, redirect, session, url_for
import hashlib
import config, model

'''
   AUTH
'''


def check_auth(username, password):
    # This function is called to check if a username password combination is valid.
    user = model.get_user_by_networkid(username)
    passw = hash_password(password)
    if user and user['password'] == passw:
        session['user_id'] = user['id']
        session['user_networkid'] = user['networkid']
        session['user_username'] = user['username']
        session['user_fullname'] = user['fullname']
        session['user_auth_level'] = user['auth_level']
        return 1
    return 0


def remove_auth():
    session.pop('user_id', None)
    session.pop('user_networkid', None)
    session.pop('user_username', None)
    session.pop('user_fullname', None)


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if config.USES_PUBCOOKIE:
            if not 'REMOTE_USER' in request.environ:
                return redirect(url_for('login'))  # not really useful here.
            elif not 'user_id' in session\
                or not 'user_networkid' in session\
                or not 'user_username' in session\
                or not 'user_fullname' in session\
                or not 'user_auth_level' in session:  # has just logged in with pubcookie...
                user = model.get_user_by_networkid(request.environ['REMOTE_USER'])
                if user:
                    session['user_id'] = user['id']
                    session['user_networkid'] = user['networkid']
                    session['user_username'] = user['username']
                    session['user_fullname'] = user['fullname']
                    session['user_auth_level'] = user['auth_level']
                    model.update_user_last_access(user['id'])
                else:
                    return redirect(url_for('access_denied'))  # doesn't exist on the system
        else:
            if not 'user_username' in session:
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def is_logged_in():
    return 'user_username' in session


def hash_password(open_text):
    return hashlib.sha224(open_text).hexdigest()