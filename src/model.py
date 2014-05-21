#
# Copyright 2014 Sinan Ussakli. All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be found in the LICENSE file.
#
import pprint
from flask import session
import database, config, auth, json, time
import psycopg2
db = database
del database


'''
    CALL LOG
'''

def get_call_log(id):
    cur = db.singleton()
    params = {'id': id}
    record = db.query(cur, '''SELECT r.id, r.user_id, username,
            to_char(r.date_of_call, 'MM/DD/YYYY') AS date_of_call, r.date_of_call AS date_of_call_raw,
            to_char(r.time_of_call, 'HH24:MI') AS time_of_call, r.time_of_call AS time_of_call_raw,
            r.from_title, r.from_who, r.from_service_floor, r.telephone_number, r.physician_name,
            r.physician_telephone_number, r.pt_name, r.pt_hosp_number, r.pt_location, r.pt_hospital,
            r.specific_request, r.staff_contacted, r.relevant_info, r.action_taken, r.follow_up,
            r.tabular_data, r.call_classification, r.viewed, r.liked, r.updated, r.created, r.flag, r.commented,
            array_to_string(array(SELECT tag FROM ''' + config.DATABASE_SCHEMA + '''.res_data_tags WHERE data_id = r.id), ',') AS tagsform
        FROM ''' + config.DATABASE_SCHEMA + '''.res_data as r INNER JOIN ''' + config.DATABASE_SCHEMA + '''.users ON (users.id = r.user_id)
        WHERE r.id = %(id)s AND deleted = false
        LIMIT 1''', params, 1)
    if record:
        record = record.copy()
    else:
        return None
    record['relevant_info'] = record['relevant_info'].strip()
    record['comments'] = get_comments(id)
    return record

def get_calls_by_patient_number(pt_hosp_number):
    cur = db.singleton(True)
    params = {'pt_hosp_number': pt_hosp_number.lower()}
    record = db.query(cur, '''SELECT id, specific_request
        FROM ''' + config.DATABASE_SCHEMA + '''.res_data
        WHERE lower(pt_hosp_number) = %(pt_hosp_number)s AND deleted = false
        ORDER BY date_of_call DESC''', params)
    return record

def save_history_call_log(id):
    recordjson = get_call_log(id)
    recordjson['updated'] = str(recordjson['updated'])
    recordjson['date_of_call'] = str(recordjson['date_of_call'])
    recordjson['time_of_call'] = str(recordjson['time_of_call'])
    recordjson['time_of_call_raw'] = None
    recordjson['date_of_call_raw'] = None
    recordjson['created'] = str(recordjson['created'])
    params = {'id': id, 'updated': 'now', 'blob': json.dumps(recordjson)}
    cur = db.singleton()
    db.execute(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.res_savehistory(id, updated, blob)
        VALUES (%(id)s, %(updated)s, %(blob)s)''', params)
    db.commit(cur)


def is_call_log_owner(user_id, call_log_id):
    cur = db.singleton()
    params = {'user_id': user_id, 'call_log_id': call_log_id}
    record = db.query(cur, '''SELECT id
        FROM ''' + config.DATABASE_SCHEMA + '''.res_data
        WHERE user_id = %(user_id)s
        AND id = %(call_log_id)s
        LIMIT 1''', params, 1)
    return record is not None


def set_call_log(form):
    errors = []
    form['updated'] = 'now'
    date_of_call = form['date_of_call']
    time_of_call = form['time_of_call']
    try:
        date_of_call = time.strptime(form['date_of_call'], '%m/%d/%Y')
    except ValueError, e:
        errors.append("Date Of Call is not formatted correctly. Only MM/DD/YYYY is accepted. ({error})".format(error=e.message))

    try:
        time_of_call = time.strptime(form['time_of_call'], '%H:%M')
    except ValueError, e:
        errors.append("Time Of Call is not formatted correctly. Only 24 hour HH:MM is accepted. ({error})".format(error=e.message))

    if (errors):
        return errors

    form['date_of_call'] = time.strftime('%Y-%m-%d', date_of_call)
    form['time_of_call'] = time.strftime('%H:%M', time_of_call)
    form['pt_hosp_number'] = form['pt_hosp_number'].strip()

    cur = db.singleton()
    db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.res_data
        SET user_id=%(user_id)s, date_of_call=%(date_of_call)s, time_of_call=%(time_of_call)s,
            from_title=%(from_title)s, from_who=%(from_who)s, from_service_floor=%(from_service_floor)s,
            telephone_number=%(telephone_number)s, physician_name=%(physician_name)s,
            physician_telephone_number=%(physician_telephone_number)s, pt_name=%(pt_name)s, pt_hosp_number=%(pt_hosp_number)s,
            pt_location=%(pt_location)s, pt_hospital=%(pt_hospital)s, specific_request=%(specific_request)s,
            staff_contacted=%(staff_contacted)s, relevant_info=%(relevant_info)s, action_taken=%(action_taken)s,
            follow_up=%(follow_up)s, tabular_data=%(tabular_data)s, call_classification=%(call_classification)s,
            updated=%(updated)s
        WHERE id = %(id)s''', form)

    # run deletes,
    if form['tagsform']:
        tags = form['tagsform'].split(',')
        for i, tag in enumerate(tags):
            tags[i] = "'" + tag + "'"
        tagsstr = ', '.join(tags)
        if not tagsstr:
            taggstr = "'not a value'"
        params = {'id': form['id']}
        db.execute(cur, 'DELETE FROM ' + config.DATABASE_SCHEMA + '.res_data_tags WHERE data_id = %(id)s AND tag NOT IN (' + tagsstr + ')', params)
    else:
        params = {'id': form['id']}
        db.execute(cur, 'DELETE FROM ' + config.DATABASE_SCHEMA + '.res_data_tags WHERE data_id = %(id)s', params)

    # run inserts
    if form['tagsform']:
        tags = form['tagsform'].split(',')
        for tag in tags:
            params = {'id': form['id'], 'tag': tag, 'user_id': session['user_id']}
            record = db.query(cur, '''SELECT id
                FROM ''' + config.DATABASE_SCHEMA + '''.res_data_tags
                WHERE data_id = %(id)s AND user_id = %(user_id)s AND tag = %(tag)s''', params)
            if not record:
                db.execute(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.res_data_tags(data_id, tag, user_id)
                    VALUES (%(id)s, %(tag)s, %(user_id)s)''', params)

    db.commit(cur)
    update_search_index(form['id'])
    return errors


def add_call_log(form):
    errors = []
    form['updated'] = 'now'
    date_of_call = form['date_of_call']
    time_of_call = form['time_of_call']
    try:
        date_of_call = time.strptime(form['date_of_call'], '%m/%d/%Y')
    except ValueError, e:
        errors.append("Date Of Call is not formatted correctly. Only MM/DD/YYYY is accepted. ({error})".format(error=e.message))

    try:
        time_of_call = time.strptime(form['time_of_call'], '%H:%M')
    except ValueError, e:
        errors.append("Time Of Call is not formatted correctly. Only 24 hour HH:MM is accepted. ({error})".format(error=e.message))

    if (errors):
        return [errors, -1]

    cur = db.singleton()

    form['date_of_call'] = time.strftime('%Y-%m-%d', date_of_call)
    form['time_of_call'] = time.strftime('%H:%M', time_of_call)
    form['pt_hosp_number'] = form['pt_hosp_number'].strip()

    id = db.query(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.res_data(
            user_id, date_of_call, time_of_call,
            from_title, from_who, from_service_floor, telephone_number, physician_name,
            physician_telephone_number,  pt_name, pt_hosp_number, pt_location, pt_hospital,
            specific_request, staff_contacted, relevant_info, action_taken, follow_up, tabular_data,
            call_classification, updated)
    VALUES (%(user_id)s, %(date_of_call)s, %(time_of_call)s,
            %(from_title)s, %(from_who)s, %(from_service_floor)s, %(telephone_number)s, %(physician_name)s,
            %(physician_telephone_number)s, %(pt_name)s, %(pt_hosp_number)s, %(pt_location)s, %(pt_hospital)s,
            %(specific_request)s, %(staff_contacted)s, %(relevant_info)s, %(action_taken)s, %(follow_up)s, %(tabular_data)s,
            %(call_classification)s, %(updated)s) RETURNING id;''', form, 1)

    id = id[0]

    if form['tagsform']:
        tags = form['tagsform'].split(',')
        for tag in tags:
            params = {'id': id, 'tag': tag, 'user_id': session['user_id']}
            db.execute(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.res_data_tags(data_id, tag, user_id)
                VALUES (%(id)s, %(tag)s, %(user_id)s)''', params)

    db.commit(cur)
    update_search_index(id)
    return [errors, id]


def delete_call_log(key):
    params = {'id': key}
    cur = db.singleton()
    db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.res_data
        SET deleted=true
        WHERE id = %(id)s''', params)
    db.execute(cur, '''DELETE FROM ''' + config.DATABASE_SCHEMA + '''.res_data_tags
        WHERE data_id = %(id)s''', params)
    db.commit(cur)


def save_tag_change_for_call(id, tag, added):
    params = {'data_id': id, 'tag': tag, 'user_id': session['user_id']}
    cur = db.singleton();
    if added:
        record = db.query(cur, '''SELECT id
                FROM ''' + config.DATABASE_SCHEMA + '''.res_data_tags
                WHERE data_id = %(data_id)s AND tag = %(tag)s''', params)
        if not record:
            db.execute(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.res_data_tags
                (data_id, tag, user_id)
                VALUES (%(data_id)s, %(tag)s, %(user_id)s)''', params)
    else:
        db.execute(cur, '''DELETE FROM ''' + config.DATABASE_SCHEMA + '''.res_data_tags
            WHERE data_id = %(data_id)s AND tag = %(tag)s''', params)
    db.commit(cur)


def increase_call_view(id):
    params = {'id': id}
    cur = db.singleton();
    db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.res_data
        SET viewed = viewed + 1
        WHERE id = %(id)s''', params)
    db.commit(cur)


def like_call_log(id):
    params = {'id': id, 'user_id': session['user_id']}
    cur = db.singleton()
    db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.res_data
        SET liked = liked + 1
        WHERE id = %(id)s''', params)
    db.commit(cur)
    db.execute(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.res_data_likes
        (user_id, res_data_id)
        VALUES (%(user_id)s, %(id)s)''', params)
    db.commit(cur)

'''
    / CALL LOG
'''

'''
   AUTOSAVE
'''


def get_autosave_form(key):
    cur = db.singleton()
    params = {'id': key}
    records = db.query(cur, '''SELECT blob
        FROM ''' + config.DATABASE_SCHEMA + '''.res_autosave
        WHERE id = %(id)s''', params, 1)
    if records is not None and len(records) > 0:
        return records[0]
    else:
        return "0"


def delete_autosave_form(key):
    cur = db.singleton()
    params = {'id': key}
    db.execute(cur, '''DELETE FROM ''' + config.DATABASE_SCHEMA + '''.res_autosave
        WHERE id = %(id)s''', params)
    db.commit(cur);


def set_autosave_form(key, data):
    cur = db.singleton()
    params = {'id': key, 'blob': data}
    frm = get_autosave_form(key)
    if frm != '0':
        db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.res_autosave
            SET blob=%(blob)s
            WHERE id = %(id)s''', params)
    else:
        db.execute(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.res_autosave (id, blob)
            VALUES (%(id)s, %(blob)s)''', params)

    db.commit(cur)

'''
   / AUTOSAVE
'''

'''
   TEMPLATE
'''


def get_template_list():
    cur = db.singleton(True)
    params = {'user_id': session['user_id']}
    records = db.query(cur, '''SELECT t.id, t.title, t.user_id, t.department_template, t.blob, s.id IS NOT NULL AS starred
        FROM ''' + config.DATABASE_SCHEMA + '''.res_template t LEFT JOIN ''' + config.DATABASE_SCHEMA + '''.res_template_star s on t.id = s.template_id
        WHERE t.user_id = %(user_id)s OR t.department_template = TRUE
        ORDER BY department_template, title''', params)
    pprint.pprint( records)
    return records


def get_template(id):
    cur = db.singleton(True)
    params = {'user_id': session['user_id'], 'id': id}
    record = db.query(cur, '''SELECT id, title, user_id, department_template, blob
        FROM ''' + config.DATABASE_SCHEMA + '''.res_template
        WHERE (user_id = %(user_id)s OR department_template = TRUE) AND id = %(id)s''', params, 1)
    return record


def add_template(data):
    cur = db.singleton()
    params = dict({'user_id': session['user_id']}.items() + data.items())

    id = db.query(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.res_template(
            title, user_id, department_template, blob)
            VALUES (%(title)s, %(user_id)s, FALSE, %(blob)s) RETURNING id;''', params, 1)
    db.commit(cur)
    return id[0]


def set_template(data):
    cur = db.singleton()
    params = data;

    db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.res_template
            SET title=%(title)s, blob=%(blob)s
            WHERE id=%(id)s''', params)
    db.commit(cur)


def delete_template(id):
    cur = db.singleton()
    params = {'user_id': session['user_id'], 'id': id}

    db.execute(cur, '''DELETE FROM ''' + config.DATABASE_SCHEMA + '''.res_template
            WHERE user_id=%(user_id)s AND id=%(id)s''', params)
    db.commit(cur)


def get_star_template(id):
    cur = db.singleton()
    params = {'user_id': session['user_id'], 'id': id}
    records = db.query(cur, '''SELECT id
        FROM ''' + config.DATABASE_SCHEMA + '''.res_template_star
        WHERE template_id = %(id)s AND user_id = %(user_id)s''', params, 1)
    if records is not None and len(records) > 0:
        return records[0]
    else:
        return "0"


def star_template(id):
    cur = db.singleton()
    params = {'user_id': session['user_id'], 'id': id}
    existing = get_star_template(id)
    if existing == '0':
        db.execute(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.res_template_star (template_id, user_id)
            VALUES (%(id)s, %(user_id)s)''', params)
    else:
        db.execute(cur, '''DELETE FROM ''' + config.DATABASE_SCHEMA + '''.res_template_star
            WHERE template_id = %(id)s AND user_id = %(user_id)s''', params)
    db.commit(cur)

    return 1 if existing == '0' else 0


def get_residents_starred_templates():
    cur = db.singleton(True)
    params = {'user_id': session['user_id']}
    records = db.query(cur, '''SELECT t.id, t.title, t.blob
        FROM ''' + config.DATABASE_SCHEMA + '''.res_template_star s INNER JOIN ''' + config.DATABASE_SCHEMA + '''.res_template t ON s.template_id = t.id
        WHERE s.user_id = %(user_id)s OR t.department_template = TRUE
        ORDER BY t.department_template DESC, t.title ASC''', params)
    return records

'''
    / TEMPLATE
'''

'''
    COMMENT
'''


def add_comment(data_id, comment):
    cur = db.singleton()
    params = {'data_id': data_id, 'user_id': session['user_id'], 'blob': comment, 'updated': 'now'}
    db.execute(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.comments(data_id, user_id, blob, updated)
        VALUES (%(data_id)s, %(user_id)s, %(blob)s, %(updated)s)''', params)
    db.commit(cur)


def get_comment(id):
    cur = db.singleton(True)
    params = {'id': id}
    records = db.query(cur, '''SELECT comments.id, comments.data_id, users.username, comments.blob, to_char(comments.updated, 'MM/DD/YYYY HH12:MI am') as updated
        FROM ''' + config.DATABASE_SCHEMA + '''.comments INNER JOIN ''' + config.DATABASE_SCHEMA + '''.users ON (comments.user_id = users.id)
        WHERE comments.id = %(id)s''', params, True)
    return records


def get_comments(id):
    cur = db.singleton(True)
    params = {'data_id': id}
    records = db.query(cur, '''SELECT comments.id, comments.data_id, users.username, comments.blob, to_char(comments.updated, 'MM/DD/YYYY HH12:MI am') as updated
        FROM ''' + config.DATABASE_SCHEMA + '''.comments INNER JOIN ''' + config.DATABASE_SCHEMA + '''.users ON (comments.user_id = users.id)
        WHERE comments.data_id = %(data_id)s
        ORDER BY comments.updated ASC''', params)
    return records


def delete_comment(id):
    cur = db.singleton()
    params = {'id': id}
    db.execute(cur, '''DELETE FROM ''' + config.DATABASE_SCHEMA + '''.comments WHERE id = %(id)s''', params)
    db.commit(cur)


def edit_comment(id, comment):
    cur = db.singleton()
    params = {'id': id, 'blob': comment}
    db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.comments
        SET blob = %(blob)s
        WHERE id = %(id)s''', params)
    db.commit(cur)


def get_users_commented_calls():
    cur = db.singleton()
    params = {'user_id': session['user_id']}
    records = db.query(cur, '''SELECT res_data.id, username, res_data.user_id, date_of_call, time_of_call,
        from_title, from_who, from_service_floor, telephone_number, physician_name,
            physician_telephone_number, pt_name, pt_hosp_number, pt_location, pt_hospital,
            specific_request, staff_contacted, relevant_info, action_taken, follow_up,
            call_classification, res_data.updated, res_data.flag, res_data.commented
        FROM ''' + config.DATABASE_SCHEMA + '''.res_data
        INNER JOIN ''' + config.DATABASE_SCHEMA + '''.users ON (res_data.user_id = users.id)
        INNER JOIN ''' + config.DATABASE_SCHEMA + '''.comments ON (res_data.id = comments.data_id)
        WHERE res_data.user_id = %(user_id)s
        AND deleted = false
        ORDER BY comments.updated DESC''', params)
    return records
'''
    / COMMENT
'''

'''
    FLAG
'''

def get_flag(call_log_id):
    cur = db.singleton()
    params = {'id': call_log_id}
    record = db.query(cur, '''SELECT flag
        FROM ''' + config.DATABASE_SCHEMA + '''.res_data
        WHERE id = %(id)s''', params, True)
    return record[0]


def get_users_flagged_calls():
    cur = db.singleton()
    params = {'user_id': session['user_id']}
    records = db.query(cur, '''SELECT res_data.id, username, user_id, date_of_call, time_of_call,
        from_title, from_who, from_service_floor, telephone_number, physician_name,
            physician_telephone_number, pt_name, pt_hosp_number, pt_location, pt_hospital,
            specific_request, staff_contacted, relevant_info, action_taken, follow_up,
            call_classification, updated, flag, commented
        FROM ''' + config.DATABASE_SCHEMA + '''.res_data
        INNER JOIN ''' + config.DATABASE_SCHEMA + '''.users ON (res_data.user_id = users.id)
        WHERE user_id = %(user_id)s
        AND deleted = false
        AND flag != 0
        ORDER BY updated DESC''', params)
    return records


def set_flag(call_log_id, flag):
    cur = db.singleton()
    params = {'id': call_log_id, 'flag': flag}
    db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.res_data SET flag = %(flag)s
        WHERE id=(%(id)s)''', params)
    db.commit(cur)


def delete_flag(call_log_id):
    cur = db.singleton()
    params = {'id': call_log_id}
    db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.res_data SET flag = 0
        WHERE id=(%(id)s)''', params)
    db.commit(cur)

'''
    / FLAG
'''

'''
    / TAG
'''
def get_tag_source():
    cur = db.singleton()
    records = db.query(cur, '''SELECT tag FROM ''' + config.DATABASE_SCHEMA + '''.tags ORDER BY tag''', None)
    tags = []
    for t in records:
        tags.append(t[0])
    return tags

def get_tags():
    cur = db.singleton(True)
    records = db.query(cur, '''SELECT t.tag, COUNT(dt.id) as count
        FROM ''' + config.DATABASE_SCHEMA + '''.tags t LEFT JOIN ''' + config.DATABASE_SCHEMA + '''.res_data_tags dt on t.tag = dt.tag
        GROUP BY t.tag;''', None)
    return records


def get_tagged_calls(tag):
    cur = db.singleton(True)
    params = {'tag': tag}
    records = db.query(cur, '''SELECT d.id, d.specific_request
        FROM ''' + config.DATABASE_SCHEMA + '''.res_data_tags dt INNER JOIN ''' + config.DATABASE_SCHEMA + '''.res_data d ON dt.data_id = d.id
        WHERE dt.tag = %(tag)s AND d.deleted=false
        ORDER BY d.id DESC''', params)
    return records


# deletes tag from the tags source, not each tagged item.
def delete_tag(tag):
    cur = db.singleton()
    params = {'tag': tag}
    db.execute(cur, '''DELETE FROM ''' + config.DATABASE_SCHEMA + '''.tags WHERE tag = %(tag)s''', params)
    db.commit(cur)


def insert_tag(form):
    cur = db.singleton()
    params = {'tag': form['tag']}
    tag = db.query(cur, '''SELECT tag FROM ''' + config.DATABASE_SCHEMA + '''.tags WHERE tag = (%(tag)s)''', params, 1)
    if tag is None:
        db.execute(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.tags (tag) VALUES(%(tag)s)''', params)
        db.commit(cur)

'''
    / TAG
'''

def get_call_classification():
    cur = db.singleton()
    params = {'id': id}
    records = db.query(cur, '''SELECT id, title
        FROM ''' + config.DATABASE_SCHEMA + '''.call_classification
        ORDER BY title''', params)
    return records


def get_pt_hospital():
    cur = db.singleton()
    params = {'id': id}
    records = db.query(cur, '''SELECT id, title
        FROM ''' + config.DATABASE_SCHEMA + '''.pt_hospital
        ORDER BY disp_order''', params)
    return records


def get_from_title():
    cur = db.singleton()
    params = {'id': id}
    records = db.query(cur, '''SELECT id, title
        FROM ''' + config.DATABASE_SCHEMA + '''.from_title
        ORDER BY id''', params)
    return records


def get_res_name():
    cur = db.singleton()
    params = {'id': id}
    records = db.query(cur, '''SELECT username as name
        FROM ''' + config.DATABASE_SCHEMA + '''.users
        ORDER BY username''', params)
    return records


'''
    SEARCH
'''

class SortBy:
    DEFAULT = 1
    RELEVANCE = 2
    DATE_DESC = 3
    DATE_ASC = 4
    ID_DESC = 5
    ID_ASC = 6

def do_search(fields, sortby):
    errors = []
    cur = db.singleton()
    query = '''SELECT res_data.id, username, date_of_call, time_of_call,
            from_title, from_who, from_service_floor, telephone_number, physician_name,
            physician_telephone_number, pt_name, pt_hosp_number, pt_location, pt_hospital,
            specific_request, staff_contacted, relevant_info, action_taken, follow_up,  call_classification, updated
        FROM ''' + config.DATABASE_SCHEMA + '''.res_data INNER JOIN ''' + config.DATABASE_SCHEMA + '''.users ON (res_data.user_id = users.id)
        WHERE deleted = false '''

    where = []
    order = ''

    if len(fields['q']):
        tsqueryfunc = 'to_tsquery' if fields['adv'] == 'on' else 'plainto_tsquery'

        if fields['meta'] == 'on' and fields['body'] == 'on':
            where.append("(fts_meta @@ " + tsqueryfunc + "('english', %(q)s) OR fts_data @@ " + tsqueryfunc + "('english', %(q)s))")
            if sortby == SortBy.DEFAULT or sortby == SortBy.RELEVANCE:
                order = "2 * ts_rank(fts_meta, " + tsqueryfunc + "('english', %(q)s), 1) + ts_rank(fts_data, " + tsqueryfunc + "('english', %(q)s), 1) DESC"
        elif fields['meta'] == 'on':
            where.append("fts_meta @@ " + tsqueryfunc + "('english', %(q)s)")
            if sortby == SortBy.DEFAULT or sortby == SortBy.RELEVANCE:
                order = "ts_rank(fts_meta, " + tsqueryfunc + "('english', %(q)s), 1) DESC"
        elif fields['body'] == 'on':
            where.append("fts_data @@ " + tsqueryfunc + "('english', %(q)s)")
            if sortby == SortBy.DEFAULT or sortby == SortBy.RELEVANCE:
                order = "ts_rank(fts_data, " + tsqueryfunc + "('english', %(q)s), 1) DESC"
    if not (fields['hosp'] == 'any' or len(fields['hosp']) == 0):
        where.append("pt_hospital = %(hosp)s")
    if not (fields['resident'] == 'any' or len(fields['resident']) == 0):
        where.append("users.username = %(resident)s")
    if not (fields['class'] == 'any' or len(fields['class']) == 0):
        where.append("call_classification = %(class)s")

    if fields['fromdt']:
        try:
            fromdt = time.strptime(fields['fromdt'], '%m/%d/%Y')
            where.append("date_of_call >= DATE('{date}')".format(date=time.strftime('%Y-%m-%d', fromdt)));
            if sortby == SortBy.DEFAULT or sortby == SortBy.DATE_DESC:
                order = order if order else "date_of_call DESC"
            elif sortby == SortBy.DATE_ASC:
                order = order if order else "date_of_call ASC"
        except ValueError, e:
            errors.append("Date Range From is not formatted correctly. Only MM/DD/YYYY is accepted. ({error})".format(error=e.message))

    if fields['todt']:
        try:
            todt = time.strptime(fields['todt'], '%m/%d/%Y')
            where.append("date_of_call <= DATE('{date}')".format(date=time.strftime('%Y-%m-%d',todt)));
            if sortby == SortBy.DEFAULT or sortby == SortBy.DATE_DESC:
                order = order if order else "date_of_call DESC"
            elif sortby == SortBy.DATE_ASC:
                order = order if order else "date_of_call ASC"
        except ValueError, e:
            errors.append("Date Range To is not formatted correctly. Only MM/DD/YYYY is accepted. ({error})".format(error=e.message))

    if fields['recent']:
        recent = int(fields['recent'])
        if fields['recenttype'] == "Days":
            where.append("date_of_call > NOW() - INTERVAL '" + str(recent) + " DAY'")
            if sortby == SortBy.DEFAULT or sortby == SortBy.DATE_DESC:
                order = order if order else "date_of_call DESC"
            elif sortby == SortBy.DATE_ASC:
                order = order if order else "date_of_call ASC"
        elif fields['recenttype'] == "Weeks":
            where.append("date_of_call > NOW() - INTERVAL '" + str(recent) + " WEEK'")
            if sortby == SortBy.DEFAULT or sortby == SortBy.DATE_DESC:
                order = order if order else "date_of_call DESC"
            elif sortby == SortBy.DATE_ASC:
                order = order if order else "date_of_call ASC"
        elif fields['recenttype'] == "Months":
            where.append("date_of_call > NOW() - INTERVAL '" + str(recent) + " MONTH'")
            if sortby == SortBy.DEFAULT or sortby == SortBy.DATE_DESC:
                order = order if order else "date_of_call DESC"
            elif sortby == SortBy.DATE_ASC:
                order = order if order else "date_of_call ASC"
        elif fields['recenttype'] == "Years":
            where.append("date_of_call > NOW() - INTERVAL '" + str(recent) + " YEAR'")
            if sortby == SortBy.DEFAULT or sortby == SortBy.DATE_DESC:
                order = order if order else "date_of_call DESC"
            elif sortby == SortBy.DATE_ASC:
                order = order if order else "date_of_call ASC"
        else:
            errors.append("Please select Days/Weeks/Months/Years at Recent field.");

    if not order:
        if sortby == SortBy.DATE_DESC:
            order = order if order else "date_of_call DESC"
        elif sortby == SortBy.DATE_ASC:
            order = order if order else "date_of_call ASC"
        elif sortby == SortBy.ID_DESC:
            order = order if order else "id DESC"
        elif sortby == SortBy.ID_ASC:
            order = order if order else "id ASC"

    if len(where):
        query = query + ' AND ' + ' AND '.join(where)
    if len(order):
        query += ' ORDER BY ' + order

    query += ' LIMIT 100 '
    pprint.pprint(query)
    records = db.query(cur, query, fields)
    return [records, errors]


def update_search_index(call_id):
    # after updating and adding a call record, the tsvector fields should be updated so that the search could work
    if call_id:
        params = {'id': call_id}
        cur = db.singleton()
        db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.res_data SET fts_meta
             = to_tsvector('english', id::text)
            || to_tsvector('english', coalesce(from_title, ''))
            || to_tsvector('english', coalesce(from_who, ''))
            || to_tsvector('english', coalesce(from_service_floor, ''))
            || to_tsvector('english', coalesce(telephone_number, ''))
            || to_tsvector('english', coalesce(physician_name, ''))
            || to_tsvector('english', coalesce(physician_telephone_number, ''))
            || to_tsvector('english', coalesce(pt_name, ''))
            || to_tsvector('english', coalesce(pt_hosp_number, ''))
            || to_tsvector('english', coalesce(pt_location, ''))
            || to_tsvector('english', coalesce(staff_contacted, ''))
            || to_tsvector('english', coalesce(call_classification, ''))
            || to_tsvector('english', coalesce(specific_request, ''))
            WHERE id = %(id)s''', params)
        db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.res_data SET fts_data
             = to_tsvector('english', coalesce(relevant_info, ''))
            || to_tsvector('english', coalesce(action_taken, ''))
            || to_tsvector('english', coalesce(follow_up, ''))
            WHERE id = %(id)s''', params)
        db.commit(cur)


'''
    / SEARCH
'''
def get_user_frontpage():
    params = {'pagination_size': config.PAGINATION_SIZE};
    if (auth.is_logged_in()):
        params['user_id'] = session['user_id']
    else:
        return {}
    cur = db.singleton()
    records = db.query(cur, '''SELECT res_data.id, username, user_id, date_of_call, time_of_call,
        from_title, from_who, from_service_floor, telephone_number, physician_name,
            physician_telephone_number, pt_name, pt_hosp_number, pt_location, pt_hospital,
            specific_request, staff_contacted, relevant_info, action_taken, follow_up,
            call_classification, updated, flag, commented
        FROM ''' + config.DATABASE_SCHEMA + '''.res_data
        INNER JOIN ''' + config.DATABASE_SCHEMA + '''.users ON (res_data.user_id = users.id)
        WHERE user_id = %(user_id)s
        AND deleted = false
        ORDER BY updated DESC
        LIMIT %(pagination_size)s''', params)
    return records


def get_list(page):
    page = page if page >= 1 else 1
    params = {'pagination_size': config.PAGINATION_SIZE, 'offset': config.PAGINATION_SIZE * (page - 1)}
    cur = db.singleton()
    records = db.query(cur, '''SELECT res_data.id, username, user_id, date_of_call, time_of_call,
        from_title, from_who, from_service_floor, telephone_number, physician_name,
            physician_telephone_number, pt_name, pt_hosp_number, pt_location, pt_hospital,
            specific_request, staff_contacted, relevant_info, action_taken, follow_up,
            call_classification, updated, commented
        FROM ''' + config.DATABASE_SCHEMA + '''.res_data INNER JOIN ''' + config.DATABASE_SCHEMA + '''.users ON (res_data.user_id = users.id)
        WHERE deleted = false
        ORDER BY id DESC
        LIMIT %(pagination_size)s OFFSET %(offset)s''', params)
    return records

'''
    USERS
'''

def update_user_last_access(key):
    cur = db.singleton()
    params = {'id': key}
    record = db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.users
        SET last_access=now()
            WHERE id=%(id)s''', params)
    db.commit(cur)


def get_users(mode = 0):
    """
    Returns users in the database
    @param mode: 0 default for all, 1 for active, 2 for passive
    :return: array of users
    """
    cur = db.singleton(True)
    params = {}
    filter = ''
    if mode == 1:
        filter = " WHERE last_access > NOW() - INTERVAL '90 DAY' "
    elif mode == 2:
        filter = " WHERE last_access <= NOW() - INTERVAL '90 DAY' "

    records = db.query(cur, '''SELECT id, fullname, username, networkid, pager, email, cellphone, deskphone,
        created, last_access, auth_level, password
        FROM ''' + config.DATABASE_SCHEMA + '''.users
        ''' + filter + '''
        ORDER BY username''', params)
    return records



def get_user(user_id):
    cur = db.singleton()
    params = {'id': user_id}
    records = db.query(cur, '''SELECT id, fullname, username, networkid, pager, email, cellphone, deskphone,
        created, last_access, auth_level, password
        FROM ''' + config.DATABASE_SCHEMA + '''.users
        WHERE id = %(id)s''', params)
    record = records[0]
    return record


def delete_user(username):
    cur = db.singleton()
    form = {'username': username}
    user = get_user_by_username(username)
    params = {'user_id': user['id']}
    count = 0
    count += db.query(cur, '''SELECT COUNT(*) FROM ''' + config.DATABASE_SCHEMA + '''.res_data WHERE user_id = %(user_id)s''', params, True)[0]
    count += db.query(cur, '''SELECT COUNT(*) FROM ''' + config.DATABASE_SCHEMA + '''.comments WHERE user_id = %(user_id)s''', params, True)[0]
    count += db.query(cur, '''SELECT COUNT(*) FROM ''' + config.DATABASE_SCHEMA + '''.res_data_likes WHERE user_id = %(user_id)s''', params, True)[0]
    count += db.query(cur, '''SELECT COUNT(*) FROM ''' + config.DATABASE_SCHEMA + '''.res_data_tags WHERE user_id = %(user_id)s''', params, True)[0]
    count += db.query(cur, '''SELECT COUNT(*) FROM ''' + config.DATABASE_SCHEMA + '''.res_template WHERE user_id = %(user_id)s''', params, True)[0]
    count += db.query(cur, '''SELECT COUNT(*) FROM ''' + config.DATABASE_SCHEMA + '''.res_template_star WHERE user_id = %(user_id)s''', params, True)[0]
    if count == 0:
        db.execute(cur, '''DELETE FROM ''' + config.DATABASE_SCHEMA + '''.users
            WHERE username = %(username)s''', form)
        db.commit(cur)
        return True

    return False

def update_user(form):
    cur = db.singleton()

    auth_query_part = ', auth_level=%(auth_level)s' if 'auth_level' in form else ''
    record = db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.users
        SET fullname=%(fullname)s, username=%(username)s, pager=%(pager)s, email=%(email)s,
            cellphone=%(cellphone)s, deskphone=%(deskphone)s''' + auth_query_part + ''' WHERE id=%(id)s''', form)
    db.commit(cur)


def create_user(form):
    cur = db.singleton()
    form['auth_level'] = int(form['auth_level'])
    if not 'password' in form:
        form['password'] = ''

    form['password'] = auth.hash_password(form['password'])
    id = -1
    error = None
    try:
        id = db.query(cur, '''INSERT INTO ''' + config.DATABASE_SCHEMA + '''.users(
                fullname, username, networkid, pager, email, cellphone, deskphone, auth_level, password)
        VALUES (%(fullname)s, %(username)s, %(networkid)s, %(pager)s, %(email)s, %(cellphone)s, %(deskphone)s,
            %(auth_level)s, %(password)s) RETURNING id''', form, True)
    except psycopg2.IntegrityError, e:
        error = e.message
    db.commit(cur)
    return [error, id]


def get_user_by_networkid(networkid):
    cur = db.singleton()
    params = {'networkid': networkid}
    userrecord = db.query(cur, '''SELECT id, fullname, username, networkid,
            pager, email, cellphone, deskphone, created, last_access, auth_level, password
        FROM ''' + config.DATABASE_SCHEMA + '''.users
        WHERE networkid = %(networkid)s''', params, 1)
    return userrecord


def get_user_by_username(username):
    cur = db.singleton()
    params = {'username': username}
    userrecord = db.query(cur, '''SELECT id, fullname, username, networkid,
            pager, email, cellphone, deskphone, created, last_access, auth_level, password
        FROM ''' + config.DATABASE_SCHEMA + '''.users
        WHERE username = %(username)s''', params, 1)
    return userrecord


def set_password(user_id, hashed_password):
    cur = db.singleton()
    params = {'id': user_id, 'password': hashed_password }
    db.execute(cur, '''UPDATE ''' + config.DATABASE_SCHEMA + '''.users SET password=%(password)s WHERE id=%(id)s''', params)
    db.commit(cur)
'''
    /USERS
'''


def total_records():
    # only useful for /list
    cur = db.singleton()
    record = db.query(cur, '''SELECT count(*) cnt
        FROM ''' + config.DATABASE_SCHEMA + '''.res_data WHERE deleted = false''', {}, 1)
    return record['cnt']