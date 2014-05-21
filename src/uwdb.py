#
# Copyright 2014 Sinan Ussakli. All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be found in the LICENSE file.
#
import psycopg2
import json
import math
import re
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps
from datetime import timedelta, datetime, date
from flask import Flask, redirect, render_template, request, session, url_for

import database, config, auth, model

db = database
del database

# the secret key used for creating seasons in Flask.
SECRET_KEY = config.SECRET_KEY

call_regex = re.compile('\\(call: (?P<callid>\d*)\\)', re.M | re.I)
pmid_regex = re.compile('\\(pmid: (?P<pmidid>\d*)\\)', re.M | re.I)
italic_regex = re.compile('\\\'\\\'\\\'(?P<italic>.*?)\\\'\\\'\\\'', re.M | re.I | re.S)
bold_regex = re.compile('\\\'\\\'(?P<bold>.*?)\\\'\\\'', re.M | re.I | re.S)
bolditalic_regex = re.compile('\\\'\\\'\\\'\\\'\\\'(?P<bolditalic>.*?)\\\'\\\'\\\'\\\'\\\'', re.M | re.I | re.S)

app = Flask(__name__)
app.config.from_object('config')

# create a logger
logger = logging.getLogger('oncalldatabase')
hdlr = logging.FileHandler(config.ACCESS_LOG_FILE)
formatter = logging.Formatter('%(asctime)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)
if not app.debug:
    file_handler = RotatingFileHandler(config.ERROR_LOG_FILE, mode='a', maxBytes=10000000, backupCount=10)
    file_handler.setLevel(logging.ERROR)
    app.logger.addHandler(file_handler)


@app.teardown_appcontext
def close_database(exception):
    db.close_database(exception)


'''
    UTIL
'''


def log_access(module, action=''):
    # use logger to write the action for tracking the events at this app.
    user = ''
    if not 'user_username' in session:
        user = 'NOUSER'
    else:
        user = session['user_username']
    logger.info(user + '\t' + module + '\t' + action)


def text_process(str):
    # process the free text areas to replace new lines, text formatting and some link syntax with actual HTML values.
    str = str.replace("\n","<br />\n")
    str = call_regex.sub('(call: <a title="Go to Call Database record" href="' + url_for('show') + '?id=\g<callid>">\g<callid></a>)', str)
    str = pmid_regex.sub('(pmid: <a target="_blank" title="Open pubmed article" href="http://www.ncbi.nlm.nih.gov/pubmed/\g<pmidid>">\g<pmidid></a>)', str)
    str = bolditalic_regex.sub('<span style="font-style:italic; font-weight:bold">\g<bolditalic></span>', str)
    str = italic_regex.sub('<span style="font-style:italic;">\g<italic></span>', str)
    str = bold_regex.sub('<span style="font-weight:bold;">\g<bold></span>', str)
    return str


def get_authorization_levels(max_level):
    # user auth level to string
    auth = []
    if max_level >= 10:
        auth.append([10, "read only user"])
    if max_level >= 100:
        auth.append([100, "regular user"])
    if max_level >= 1000:
        auth.append([1000, "power user"])
    if max_level >= 10000:
        auth.append([10000, "administrator"])
    return auth


def day_of_week(day):
    return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day]


def pagination(page):
    # outputs in array of label(string), value(int), and current(boolean) to be used at the pagination template.
    # this function is only useful for the list view as it gets the total size of all records in the database.
    pagination = []
    total = model.total_records()
    last = int(math.ceil(total / config.PAGINATION_SIZE))

    start = page - 4
    end = page + 4
    if start < 1:
        end += 1 - start
        start = 1

    if end > last:
        end = last

    pagination.append({'label': 'first', 'value': 1, 'current': 1 == page})
    for i in range(start, end + 1):
        pagination.append({'label': i, 'value': i, 'current': i == page})

    pagination.append({'label': 'last', 'value': last, 'current': last == page})
    return pagination

'''
    /UTIL
'''


def write_enabled(f):
    # Locks the database in read only mode if the READ_ONLY flag at configuration is set,
    # this is a filter on /edit and /new. Comments and flagging etc would still work.
    @wraps(f)
    def decorated(*args, **kwargs):
        if config.READ_ONLY:
            return redirect(url_for('read_only'))
        return f(*args, **kwargs)
    return decorated

'''
    ROUTES
'''


@app.route('/')
@auth.requires_auth
def home():
    # Home page
    # Lists user's calls, flagged calls, commented calls.
    log_access('home')
    records = model.get_user_frontpage()
    flaggedrecords = model.get_users_flagged_calls()
    commentedrecords = model.get_users_commented_calls()
    renderwelcome = False
    if (records):
        # if there is no record you can edit, show the generic welcome page.
        if (records[0]['date_of_call']  < date.today() - timedelta(days=config.DISABLE_EDIT_AGE)):
            renderwelcome = True

    return render_template("home_entries.html",
                           latestrecords = records,
                           flaggedrecords = flaggedrecords,
                           commentedrecords = commentedrecords,
                           renderwelcome = renderwelcome)


@app.route('/new', methods=['GET', 'POST'])
@auth.requires_auth
@write_enabled
def new():
    # New call record form.
    # If no errors, forwards to /edit
    errors = []
    if not session['user_auth_level'] >= 100: #  read write
        log_access('new', 'access_denied: user is not read/write user or above')
        return render_template('access_denied.html')

    if request.method == 'POST':
        form = request.form.copy()
        [errors, id] = model.add_call_log(form)
        log_access('new', 'form recorded ' + str(id))

        model.delete_autosave_form(session['user_username'])
        if not errors:
            return redirect(url_for('edit', id=id))

    else:
        log_access('new')
        form = {'username': session['user_username'], 'user_id': session['user_id']}
    return render_template('new.html', form=form,
                            call_classification=model.get_call_classification(),
                            pt_hospital=model.get_pt_hospital(),
                            from_title=model.get_from_title(),
                            tagsource=model.get_tag_source(),
                            errors=errors)


@app.route('/edit', methods=['GET', 'POST'])
@auth.requires_auth
@write_enabled
def edit():
    # Edit call record form.
    errors = []
    message = None
    # can edit?
    if not session['user_auth_level'] >= 100:  # read write
        log_access('edit', 'access_denied: user is not read/write user or above record id:' + request.args['id'])
        return render_template('access_denied.html')

    # is a form submitted?
    if request.method == 'POST':
        form = request.form.copy()
        log_access('edit', 'posted form: ' + form['id'])
        if model.get_call_log(form['id'])['created'] < datetime.today() - timedelta(days=config.DISABLE_EDIT_AGE):
            # unless administrator, check for age of the record.
            if not session['user_auth_level'] >= 10000:  # not administrator
                log_access('edit', 'form older than disable edit age')
                errors.append("This record is older than " + str(config.DISABLE_EDIT_AGE) + " days. You cannot edit this record. This is the error.")
        # unless administrator, check for the ownership of the record.
        elif session['user_auth_level'] >= 10000 or model.is_call_log_owner(session['user_id'], form['id']):
            model.save_history_call_log(request.form['id'])
            model.delete_autosave_form(request.form['id'])
            errors = model.set_call_log(form)
            if not errors:
                log_access('edit', 'form recorded ' + str(request.form['id']))
                form = model.get_call_log(request.form['id'])
                message = "Record saved. <a href='" + url_for("show", id=form['id']) + "'>Show record.</a>"
        else:
            log_access('edit', 'access_denied ' + str(request.form['id']))
            return render_template('access_denied.html')
    # initial display of the unedited form?
    elif request.method == 'GET':
        id = int(request.args['id'])
        record = model.get_call_log(id)
        log_access('edit', 'id: ' + str(id))
        if record['created'] < datetime.today() - timedelta(days=config.DISABLE_EDIT_AGE):
            if not session['user_auth_level'] >= 10000:  # not administrator
                errors.append("This record is older than " + str(config.DISABLE_EDIT_AGE) + " days. You cannot edit this record. Saving will result in an error.")

        if record['user_id'] != session['user_id']:
            if not session['user_auth_level'] >= 10000:  # not administrator
                log_access('edit', 'access_denied: userid != records owner id')
                return render_template('access_denied.html')

        form = record
    else:
        return render_template('error.html')

    tagsource = model.get_tag_source()
    return render_template('new.html', form = form,
                           call_classification = model.get_call_classification(),
                           pt_hospital = model.get_pt_hospital(),
                           from_title = model.get_from_title(),
                           tagsource = model.get_tag_source(),
                           errors = errors,
                           message = message)


@app.route('/search', methods=['GET'])
@auth.requires_auth
def search():
    # Search page
    log_access('search')
    records = []
    errors = []
    recordidslist = []
    args = request.args.copy()
    message = ''
    if args.has_key('q'):
        log_access('search', 'query: ' + request.query_string)
        sortby = model.SortBy.DEFAULT

        if not args.has_key('meta'):
            args['meta'] = ''
        if not args.has_key('body'):
            args['body'] = ''
        if not args.has_key('adv'):
            args['adv'] = ''

        if args['sortby'] == 'default':
            sortby = model.SortBy.DEFAULT
        elif args['sortby'] == 'relevance':
            sortby = model.SortBy.RELEVANCE
        elif args['sortby'] == 'date_desc':
            sortby = model.SortBy.DATE_DESC
        elif args['sortby'] == 'date_asc':
            sortby = model.SortBy.DATE_ASC
        elif args['sortby'] == 'id_desc':
            sortby = model.SortBy.ID_DESC
        elif args['sortby'] == 'id_asc':
            sortby = model.SortBy.ID_ASC

        try:
            [records, errors] = model.do_search(args, sortby)
        except psycopg2.ProgrammingError, e:
            cur = db.singleton()
            db.commit(cur)
            message = e.pgerror

    for record in records:
        recordidslist.append(str(record['id']))
    recent_type = [{"title": ""}, {"title": "Days"}, {"title": "Weeks"}, {"title": "Months"}, {"title": "Years"}]
    sort_by = [{"title": "By Date: newest first", "value": "date_desc"},
               {"title": "By Date: oldest first", "value": "date_asc"},
               {"title": "By Id: largest first", "value": "id_desc"},
               {"title": "By Id: smallest first", "value": "id_asc"},
               {"title": "Most relevant first", "value": "relevance"},
               {"title": "Default", "value": "default"}]
    return render_template('search.html',
                           form=request.args,
                           records=records,
                           call_classification=model.get_call_classification(),
                           res_name=model.get_res_name(),
                           pt_hospital=model.get_pt_hospital(),
                           recent_type=recent_type,
                           sort_by=sort_by,
                           message=message,
                           errors=errors,
                           recordidslist='-'.join(recordidslist))


@app.route('/list', methods=['GET'])
@auth.requires_auth
def list():
    # List page
    page = int(request.args['p']) if 'p' in request.args else 1
    log_access('list', 'page: ' + str(page))
    page = page if page >= 1 else 1
    return render_template('list.html',
                           records = model.get_list(page),
                           pagination = pagination(page))


@app.route('/show', methods=['GET'])
@auth.requires_auth
def show():
    # Shows a single record
    errors = []
    if request.args.has_key('id'):
        id = int(request.args['id'])
        log_access('show', 'id: ' + str(id))
        model.increase_call_view(id)
        record = model.get_call_log(id)
        if not record:
            return redirect(url_for('access_denied'))

        if record['date_of_call_raw'] < date.today() - timedelta(days=config.WARN_OLD_RECORD*365):
            errors.append("This record is older than " + str(config.WARN_OLD_RECORD) + " years. The contents of this record could be stale.")

        record['relevant_info'] = text_process(record['relevant_info'])
        record['action_taken'] = text_process(record['action_taken'])
        record['follow_up'] = text_process(record['follow_up'])
        record['day_of_week'] = day_of_week(record['date_of_call_raw'].weekday())
        return render_template('show.html',
                               record=record,
                               tagsource=model.get_tag_source(),
                               errors=errors )
    else:
        return render_template('error.html')


@app.route('/me', methods=['GET', 'POST'])
@auth.requires_auth
def me():
    # My details page, allows users to update their basic information.
    message = None
    log_access('me')

    if request.method == 'POST':
        model.update_user(request.form)
        log_access('me', 'saved form')
        message = "Saved."
        if request.form['username'] != session['user_username']:
            auth.remove_auth()
            return redirect(url_for('me'))

    form=model.get_user(session['user_id'])
    return render_template('user_edit.html',
                           form=form,
                           message=message,
                           user_auth_levels=get_authorization_levels(session['user_auth_level']),
                           form_action_url=url_for('me'),
                           title="My Details",
                           delete_button = False,
                           change_password_button = True)


@app.route('/users', methods=['GET'])
@auth.requires_auth
def users():
    # Lists all users in 2 groups, active past 90 days, otherwise.
    log_access('users')
    return render_template('users.html',
                           activeusers=model.get_users(1),
                           passiveusers=model.get_users(2))


@app.route('/users/new', methods=['GET', 'POST'])
@auth.requires_auth
def new_user():
    # Create a new user
    log_access('users/new')
    form = None
    message = None
    errors = []
    if request.method == 'POST':
        form = request.form.copy()
        log_access('users/new', 'posted')
        # must be a power user or better.
        if session['user_auth_level'] >= 1000: # power user
            [error, id] = model.create_user(form)
            if not error:
                return redirect(url_for('edit_user', username=form['username']))
            else:
                errors.append(error)
        else:
            log_access('users/new', 'access_denied')
            return redirect(url_for('access_denied'))
    return render_template('user_edit.html',
                       form=form,
                       message=message,
                       errors=errors,
                       user_auth_levels=get_authorization_levels(session['user_auth_level']),
                       form_action_url=url_for('new_user'),
                       title="New User",
                       delete_button = False,
                       change_password_button = False)


@app.route('/user/<username>', methods=['GET'])
@auth.requires_auth
def user(username):
    # Shows a single user
    log_access('user', 'viewed: ' + username)
    form=model.get_user_by_username(username)
    return render_template('user_show.html', form=form)


@app.route('/user/<username>/delete', methods=['GET'])
@auth.requires_auth
def delete_user(username):
    # Deletes a user from the system.
    # In order to delete that user must have no activity in the system.
    if session['user_auth_level'] >= 1000:
        message = None
        deleted = model.delete_user(username)
        if deleted:
            log_access('users/delete', 'deleted user: ' + username)
            return redirect(url_for('users'))
        else:
            log_access('users/delete', 'error deleting user: ' + username)
            return render_template('generic_error.html', title='Delete User Failed', message='The user ' + username
                + ' has one of following in the system: an entry, comment, like, template, starred template or tag. '
                + 'As users are related to the entries of the system, deleting them will create problems. '
                + 'Deleting a user is only possible when they are created by mistake, and they are deleted immediately.')
    else:
        log_access('users/delete', 'access_denied deleting: ' + username)
        return redirect(url_for('access_denied'))


@app.route('/user/<username>/edit', methods=['GET', 'POST'])
@auth.requires_auth
def edit_user(username):
    # Edits information of a user.
    if session['user_auth_level'] >= 1000 or session['user_username'] == username:
        log_access('users/edit', 'editing: ' + username)
        message = None
        if request.method == 'POST':
            log_access('users/edit', 'posted form')
            model.update_user(request.form)
            message = "Saved."

        form=model.get_user_by_username(username)
        return render_template('user_edit.html',
                               form=form,
                               message=message,
                               user_auth_levels=get_authorization_levels(session['user_auth_level']),
                               form_action_url=url_for('edit_user', username=username),
                               title="Edit User",
                               delete_button = session['user_auth_level'] >= 1000,
                               change_password_button = not config.USES_PUBCOOKIE)
    else:
        log_access('users/edit', 'access_denied editing: ' + username)
        return redirect(url_for('access_denied'))


@app.route('/user/<username>/password', methods=['GET', 'POST'])
@auth.requires_auth
def edit_user_password(username):
    # Updates password of a user on non PubCookie setups.
    message = None
    errors = []
    if session['user_auth_level'] >= 10000 or session['user_username'] == username: #  administrator access
        log_access('users/password')
        if request.method == 'POST':
            log_access('users/password', 'posted form')
            user_id = request.form['user_id']
            current_pw = request.form['cur_password'] if 'cur_password' in request.form else ''
            new_pw = request.form['new_password']
            again_pw = request.form['again_password']
            user = model.get_user(user_id)
            current_hash_pw = auth.hash_password(current_pw)
            if session['user_auth_level'] >= 10000 and session['user_id'] != user_id:
                current_hash_pw = user['password']

            if not user['password'] == current_hash_pw:
                errors.append("Current Password is incorrect")
            elif new_pw == '':
                errors.append("New password is empty")
            elif not new_pw == again_pw:
                errors.append("Passwords don't match")
            else:
                model.set_password(user_id, auth.hash_password(new_pw))
                message = "Saved."

        form=model.get_user_by_username(username)
        return render_template('user_edit_password.html',
                               form=form,
                               errors=errors,
                               message=message)
    else:
        log_access('users/password', 'access_denied changing password for: ' + username)
        return redirect(url_for('access_denied'))


@app.route('/tags', methods=['GET', 'POST'])
@auth.requires_auth
def tags():
    # Lists all tags defined in the system.
    log_access('tags')
    if request.method == 'POST':
        if session['user_auth_level'] >= 1000:
            log_access('tags', 'posted form')
            model.insert_tag(request.form)
        else:
            log_access('tags', 'access_denied adding tag')
            return redirect(url_for('access_denied'))

    return render_template('tags.html',tags=model.get_tags(), tag=None)


@app.route('/tag/<tag>', methods=['GET'])
@auth.requires_auth
def tag(tag):
    # Shows a single tag and it's records.
    log_access('tags', 'for tag: ' + tag)
    taggedcalls=model.get_tagged_calls(tag)

    return render_template('tags.html', tags=model.get_tags(), tag=tag, taggedcalls=taggedcalls)


@app.route('/printcalls')
def printcalls():
    # Interface to print calls.
    # Summarizes them at top, and prints a call per page.
    log_access('printcalls', 'ids: ' + request.args['id'])
    ids = str(request.args['id']).split('-')
    ids.sort()
    records = []
    for id in ids:
        id = int(id)
        record = model.get_call_log(id).copy()
        record['relevant_info'] = text_process(record['relevant_info'])
        record['action_taken'] = text_process(record['action_taken'])
        record['follow_up'] = text_process(record['follow_up'])
        record['tagsform'] = record['tagsform'].split(',') if record['tagsform'] else []
        record['day_of_week'] = day_of_week(record['date_of_call_raw'].weekday())
        records.append(record)
    return render_template('printcalls.html',
        records=records)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Login interface for non PubCookie setups.
    log_access('login')
    # Is form submitted?
    if request.method == 'POST':
        log_access('login', 'posted form')
        if auth.check_auth(request.form['username'], request.form['password']):
            return redirect(url_for('home'))
    # Is it a PubCookie setup?
    if not config.USES_PUBCOOKIE:
        log_access('login', 'not using pubcookie')
        return render_template('login.html')
    # Show the form.
    else:
        log_access('login', 'using pubcookie only, error message')
        return render_template('pubcookie_only.html', uwnetid=request.environ['REMOTE_USER'] if 'REMOTE_USER' in request.environ else None)


@app.route('/logout')
def logout():
    # Logs out the user by clearing the login on PubCookie and clearing the session.
    log_access('logout')
    auth.remove_auth()
    if config.USES_PUBCOOKIE:
        return redirect("/LOGOUT-CLEARLOGIN")
    else:
        return redirect(url_for('home'))


@app.route('/read_only')
def read_only():
    # Renders read only error.
    log_access('read_only')
    return render_template('read_only.html')


@app.route('/access_denied')
def access_denied():
    # Renders access denied error.
    log_access('access_denied')
    return render_template('access_denied.html')


@app.route('/help')
def help():
    # Renders help page.
    log_access('help')
    return render_template('help.html')


@app.route('/ajax', methods=['GET', 'POST'])
def ajax():
    # Utility entry point for various functions that are triggered by the javascript.
    action = request.args['action']
    log_access('ajax', 'query' + request.query_string)

    # AutoSaveForm is used to recover any edits on the calls when users browser closes for an unintended reason.
    if action == 'setautosaveform':
        model.set_autosave_form(request.args['key'], json.dumps(request.form))

    elif action == 'getautosaveform':
        return model.get_autosave_form(request.args['key'])

    elif action == 'deleteautosaveform':
        model.delete_autosave_form(request.args['key'])

    # Templates are quick text blobs used for editing the calls.
    elif action == 'gettemplatelist':
        return json.dumps(model.get_template_list())

    elif action == 'addtemplate':
        id = model.add_template(request.form)
        return json.dumps(model.get_template(id))

    elif action == 'settemplate':
        model.set_template(request.form)
        return json.dumps(model.get_template(request.form['id']))

    elif action == 'deletetemplate':
        model.delete_template(request.form['id'])

    elif action == 'startemplate':
        return json.dumps(model.star_template(request.form['id']))

    elif action == 'getresidentsstarredtemplates':
        return json.dumps(model.get_residents_starred_templates())

    # Commenting related functions
    elif action == 'addcomment':
        model.add_comment(request.args['key'], request.form['comment'])
        return json.dumps(model.get_comments(request.args['key']))

    elif action == 'deletecomment':
        id = request.args['comment_id']
        comment = model.get_comment(id)
        if session['user_auth_level'] >= 10000 or comment['username'] == session['user_username']: # administrator
            model.delete_comment(id)

    elif action == 'savecomment':
        id = request.args['comment_id']
        comment = model.get_comment(id)
        if session['user_auth_level'] >= 10000 or comment['username'] == session['user_username']: # administrator
            model.edit_comment(id, request.form['comment'])

    elif action == 'getcomments':
        call_id = request.args['key']
        comments = model.get_comments(call_id)
        for comment in comments:
            comment['blob'] = text_process(comment['blob'])
        return json.dumps(comments)

    # Deletes a call record.
    elif action == 'deletecalllog':
        key = request.args['key']
        if session['user_auth_level'] >= 10000 \
                or (model.is_call_log_owner(session['user_id'], key) and model.get_call_log(key)['created'] >= datetime.today() - timedelta(days=config.DISABLE_EDIT_AGE)): #  administrator
            model.delete_call_log(key)

    # Returns calls of a specific patient by the patients hospital number.
    elif action == 'searchforpatientnumber':
        key = request.args['key']
        key = key.strip()
        return json.dumps(model.get_calls_by_patient_number(key))

    # Tag related
    elif action == 'deletetag':
        model.delete_tag(request.args['tag'])

    elif action == 'saveTagChange':
        model.save_tag_change_for_call(int(request.args['id']), request.args['tag'], int(request.args['added']))

    # Liking a call, currently there is no limit on how many times you can like a record.
    elif action == 'like':
        key = int(request.args['id'])
        model.like_call_log(key)
        call = model.get_call_log(key)
        return str(call['liked'])

    # Flags a record
    elif action == 'flag':
        key = int(request.args['id'])
        flag = int(request.args['flag'])
        flag_state = model.get_flag(request.args['id'])
        if flag_state == flag:
            model.delete_flag(request.args['id'])
        else:
            model.set_flag(key, flag)

        return str(model.get_flag(request.args['id']))

    return '1'


if __name__ == '__main__':
    app.run(debug='true', host='0.0.0.0', port=5000, threaded=False)
#        app.run(host='0.0.0.0')

