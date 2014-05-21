#
# Copyright 2014 Sinan Ussakli. All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be found in the LICENSE file.
#
from datetime import date
# configuration
SECRET_KEY = 'CHANGE_ME'      # use a unique secret key
DATABASE_NAME = "postgres"       # name of the database to connect
DATABASE_SCHEMA = "residents"  # database schema, public in general.
DATABASE_HOST = "127.0.0.1"    # database host
DATABASE_USER = "residents"    # database user
DATABASE_PWD = "RESIDENTS_PWD" # database user's pass.
PAGINATION_SIZE = 100          # number of call records to show on any screen that lists items.
READ_ONLY = False              # True makes /edit and /new not to work.
DISABLE_EDIT_AGE = 90          # Disables the editing of a record after X amount of days
WARN_OLD_RECORD = 3            # Creates a warning on the view of a record after X amount of years
USES_PUBCOOKIE = False         # Uses the pubcookie auth see: http://www.pubcookie.org/
ERROR_LOG_FILE = '/path/to/script/location/uwdb.log'
ACCESS_LOG_FILE = '/path/to/script/location/access.' + date.today().isoformat() + '.log'