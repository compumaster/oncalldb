# Open-Source Online Database for Clinical Pathology Consults #

## Overview ##


One effective method for assessing core competencies in Clinical Pathology is through evaluation of a log of clinical cases.  This application was created to log resident consults received on Clinical Pathology call and is currently used by the Laboratory Medicine residents at the University of Washington.  It uses the Flask python framework and a PostgreSQL instance hosted on a server. The application is configured to use Apache and University of Washington's pubCookie web authentication services but can be configured to use forms authentication.

The application offers:

* Interfaces to track incoming calls to on-call residents, as well as search, list and view each record.
* Search functionality that allows residents to search the meta-data fields and free text regions separately and allows saving search queries for future use and reporting.
* Formatted printing for presenting cases during call rounds, with an option for excluding protected health information (from metadata) for educational purposes.
* Features such as templates for pre-determined text structures, insertion of tables for specific call types, automatic saving of non-submitted data to the server for auto-restore, tagging, flagging, linking to other database entries and PubMed records, and automated search for a patient’s previous entries in the database when a medical record number is entered.
* User commenting (eg. faculty) on other user entries for follow up and education and voting for useful entries to make them more visible.
* Multiple user account levels, allowing some users permission to create and delete other users and maintain various aspects of the system.

This application has been tested on all major browsers and operating systems.  An instance has been used by the University of Washington Department of Laboratory Medicine since July 2013.

Details about the tool and its development were presented at the 2014 meeting for the Academy of Clinical Laboratory Physicians and Scientists: "An Open-Source Online Database for Clinical Pathology Consults", Cigdem Himmetoglu Ussakli, Patrick C. Mathias, Sinan Ussakli, Noah G. Hoffman, ACLPS 2014, San Francisco, CA.

## Directory Structure ##

	$ tree -d -L 2 --charset=ASCII lmr_database/
	lmr_database/
	|-- database
	`-- src
	 |-- static
	 |-- templates
	 `-- uwdb

    [D] database  - contains schema of the database and data of some utility tables.
	[D] src       - sources.
	[D] static    - contains all assets, also javascript scripts.
    [D] templates - contains Jinja templates used in Flask.

    auth.py      - everything about authenticating to the application, user check etc.
    database.py  - database connection layer.
    model.py     - model, all of the database queries are here. Note, we are using direct SQL queries.
    uwdb.py      - controller, all of the business logic, controller, and view port handling, some utility functions.

    config.py    - all configuration of the application, database connection string, logging, and other configurations.
    uwdb.wsgi    - wsgi gate for Apache.


## Dependencies ##

    Apache2    - no specific version, we're using latest as of 2013.
    Python     - version 2.7
    Postgresql - version 8.4, database connection configuration is at /src/config.py
    Flask      - Installation: http://flask.pocoo.org/docs/installation/#installation
	psycopg2   - Python PostgreSQL2 connection


    The client side uses Twitter Bootstrap and jQuery and several plugins they're all checked in to /src/static/assets.
    Site's JavaScipt file  /src/static/assets/js/site.js
    Site's CSS file        /src/static/assets/css/site.css
    There are many javascript extensions installed. They're listed at the end of /templates/layout.html.
    Site's CSS's HTML insert point is at /templates/head.html

## A very quick installation guide

Check the [INSTALL.md](INSTALL.md) file for a more detailed installation guide.  The information below doesn't consider python virtual environments, https, or database security, but it gets you the app up and running as fast as possible.

## Apache configuration ##


### pubcookie ###


This app is configured to work either with pubcookie or with basic HTML forms login. If your organization uses pubcookie you need to install pubcookie and enable it at Apache, you'll need similar configuration at [www.pubcookie.org](http://www.pubcookie.org/docs/install-mod_pubcookie.html#config), complete guide is at the same page.


### Apache Site configuration ###

The apache settings:

    <VirtualHost *:80>
            ServerAdmin user@domain.com

            # redirect user to https
            RewriteEngine On
            RewriteCond %{HTTPS} off
            RewriteRule (.*) https://%{HTTP_HOST}%{REQUEST_URI}
    </VirtualHost>

    <VirtualHost *:443>
            ServerAdmin user@domain.com

            DocumentRoot /path/to/script/location

            # certs used for https
            SSLEngine on
            SSLCertificateFile /etc/ssl/certs/certificatefile.pem
            SSLCertificateKeyFile  /etc/ssl/certs/private/certificatefilekey.key

            # main entry point for the wsgi application
            WSGIScriptAlias /oncalldb /path/to/script/location/uwdb.wsgi

			# if you are using pubcookie you need this configuration or else just remove it.

			# [[[ pubcookie configuration start ]]]

			# in order to get the pubcookie to work, a subdirectory is required.
            # or else the wsgi conflicts with the pubcookie's authentication response.
            <Directory /home/sinan/oncalldb/oncalldb>
                    Options FollowSymLinks
                    Order deny,allow
                    allow from all
                    # pubcookie configuration
                    AuthType UWNetID
                    AuthName "OnCall Database"
                    PubcookieAppID "OnCall Database"
                    require valid-user
            </Directory>

            # these two location matches are for logout.
            <LocationMatch .*/LOGOUT-REDIRECT.*>
                    AuthType UWNetID
                    require valid-user
                    PubcookieEndSession redirect
            </LocationMatch>

            <LocationMatch .*/LOGOUT-CLEARLOGIN.*>
                    AuthType UWNetId
                    require valid-user
                    PubcookieEndSession clearLogin
            </LocationMatch>

			# [[[ pubcookie configuration end ]]]

			ErrorLog ${APACHE_LOG_DIR}/error.log

            # Possible values include: debug, info, notice, warn, error, crit, alert, emerg.
            LogLevel info

            CustomLog ${APACHE_LOG_DIR}/access.log combined
    </VirtualHost>

## Logs ##


3 types of log files:

* Application's users' access log: access.{date}.log at the path defined in the `config.py`
* Application's exceptions are logged to the log file defined in the `config.py`
* Apache's log as defined on apache configuration. This doesn't contain any useful data other than apache issues.


## Author ##


Sinan Ussakli, Copyright (c) 2013, 2014

http://software.ussakli.net
