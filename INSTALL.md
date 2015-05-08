# Installation #
Steps:

- Start with a clean VM with Ubuntu 14.04 LTS. This guide should work on any recent Ubuntu distro.

## Files ##
- Create www folder under user. So if your user folder is /home/username the /path/to/script/location is now /home/username/www
- Deploy contents of src folder there.
- Edit uwdb.wsgi file and replace the /path/to/script/location to point to this folder.

## Install ##
### Apache with mod_wsgi ###
- Apache:
- `sudo aptitude install apache2 apache2.2-common apache2-mpm-prefork apache2-utils libexpat1 ssl-cert`
- Check the server IP to see if Apache serves.
- Install mod_wsgi:
- `sudo aptitude install libapache2-mod-wsgi`
- Restart Apache:
- `sudo service apache2 restart`

### PostgreSQL ###
- Install postgreSQL:
- `sudo apt-get install postgresql postgresql-contrib`
- Install postgreSQL development packages: 
- `sudo apt-get install postgresql-server-dev-9.3 libpq-dev`
- Setup Postgre credentials:
- `sudo -u postgres psql postgres`
- `\password postgres`
- `ctrl d` to exit.
- Change postgres' listen address: (assuming we installed 9.3)
- `sudo nano /etc/postgresql/9.3/main/postgresql.conf`
- Change `listen_addresses = '*'`
- Relax the connection rules:
- `sudo nano /etc/postgresql/9.3/main/pg_hba.conf`
- Add or change to `host all all 0.0.0.0/0 md5`
- Restart postgresql:
- `sudo service postgresql restart`

Now you should be able to login to postgres via your computer. You may want to revert these changes to more strict for extra security.

- Open pgAdminIII at your computer,
- Connect to server
- Create a new login role role name: `residents` password: `pick a new password`, give all rights or necessary rights.
- Open a SQL Query dialog and paste the `res_data_schema.backup` and execute the script.
- Open another SQL Query dialog and paste the `res_data.backup` and execute the script.
- Don't close the pgAdminIII (or read the create a new user section below)

### Python 2.7, Flask, psycopg2 ###
- Install python 
- `sudo apt-get install python2.7 python-dev`
- Install pip:
- `sudo apt-get install python-pip`
- Install Flask:
- `sudo pip install Flask`
- Install psycopg2
- `sudo pip install psycopg2`
- Edit Apache Sites Enabled Conf (this is actually a symlink, but we're cutting corners)
- `sudo nano /etc/apache2/sites-enabled/000-default.conf`
- If you don't have HTTPS and no pubCookie use this (full Apache configuration is at readme file).

		<VirtualHost *:80>
        ServerAdmin user@domain.com

        DocumentRoot /path/to/script/location

        # main entry point for the wsgi application
        WSGIScriptAlias /oncalldb /path/to/script/location/uwdb.wsgi

        
		ErrorLog ${APACHE_LOG_DIR}/error.log

        # Possible values include: debug, info, notice, warn, error, crit, alert, emerg.
        LogLevel info

        CustomLog ${APACHE_LOG_DIR}/access.log combined
		</VirtualHost>
		
		# Either add this here, or change the apache2.conf
		<Directory /path/to/script/location>
                Options All
                AllowOverride All
                Require all granted
        </Directory>


- Restart the apache
- `sudo service apache2 restart`

### Update the script's configuration ###

- Create a logs folder.
- Change the logs folder's owner to www-data:www-data
- Edit the `config.py` file.
- Update the `ERROR_LOG_FILE` and `ACCESS_LOG_FILE` to point to this folder (replace /path/to/script/location).
- Change the DATABASE_ configuration to be same as the database you restored at PostgreSQL step.
- For application security give a new SECRET_KEY
- Restart the Apache
- `sudo service apache2 restart`
- Go to the website http://sites-address.com/oncalldb 
- You should be greeted by "Login The resource you're trying to access is restricted." error and asking you to login

### Create a new user to log-in ###

- Go back to the pgAdminIII and go to Schemas/Residents/Tables/users right click, scripts, insert script and roughly change the insert script to look like following:

		INSERT INTO residents.users(
            fullname, username, networkid, pager, email, cellphone, deskphone, 
            auth_level, password)
    	VALUES ('Full Name', 'administrator', 'administrator', '', '', '', '',  
            10000, 'd63dc919e201d7bc4c825630d2cf25fdc93d4b2f0d46706d29038d01');

The passwords are calculated by SHA224 and above is `password` as password.

### Things to consider ###
- Some templates still have University of Washington related strings, you may want to clean them up. All templates are in the /src/templates folder
 
### Troubleshooting ###
If at any time the application gives Internal server error, or some exception check this file:
`sudo tail /var/log/apache2/error.log`

It will give you all python script errors including missing python packages, directory write permission errors, database connection issues, and so on.

Make sure to restart apache to make sure if the python script is reloaded by `sudo service apache2 restart`

## Author ##
Sinan Ussakli, Copyright (c) 2013, 2014

http://software.ussakli.net
