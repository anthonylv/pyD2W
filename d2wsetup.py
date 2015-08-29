#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Set up a Drupal to WordPress migration project.

Sets a Drupal to WordPress migration project by creating
project file folders and working databases. 
"""

import sys, getopt, os
import display_cli as cli
import settings
from os.path import expanduser
from database_interface import Database
from MySQLdb import OperationalError


def print_usage():
    """Print usage instructions to the screen.

    For the usage format, see http://en.wikipedia.org/wiki/Usage_message.
    """
    print """\
    Usage: d2wprojectsetup.py [-h --help | -p=path]

    Options:
    -p path, --path path
        Path to the project

    -h, --help
        Display options
    """    

def run_setup(path):
    """Setup the project.

    Args:
        path: Path to the project location.
    """
    print "The process will create new directories in "+path
    answer = cli.query_yes_no("Are you sure you want to continue?", "no")
    if answer:
        create_directory(path)
        create_directory(os.path.join(path, "Analysis"))
        create_directory(os.path.join(path, "Archives"))
        create_directory(os.path.join(path, "Exports"))
        create_directory(os.path.join(path, "Specifications"))
        create_directory(os.path.join(path, "SQL"))

        setup_databases()
    else:
        print "Project setup aborted"
        

def get_default_project_path():
    """Gets the default project path.

    Returns:
        Path to the project directory
    """    
    project_path = os.getcwd()+os.sep+"new_project"
    try:
        project_path = settings.get_default_project_path()
    except AttributeError:
        print "Settings file does not have a default project path."
        print "Using default: {}".format(project_path)
    return project_path
    

def create_directory(path):
    """Create a directory.
    
    Args:
        path: Path to the project location.    
    """
    print "Creating directory: {}...".format(path)
    if not os.path.exists(path):
        try:
            os.makedirs(path)
            print "...done"
        except OSError as e:
            print "Sorry there was a problem creating the directory: {}".format(e.strerror)            
            if not path:
                print "The path string is empty"
    else:
        print "The directory {} already exists".format(path)


def setup_databases():
    """Create local working databases.
    
    Create the local working databases using a user with CREATE privilege
    but assign those databases to the migration user who may have more
    limited privileges.
    """
    continue_scipt = True
    """
    # Uncomment if you want to prompt for an admin user credentials
    # Comment out the section where credentials are taken from settings file
    print "About to create working databases. Please enter credentials for a database user with CREATE privilege."
    # We need a user with CREATE privilege to create the tables
    admin_user, admin_password = cli.ask_credentials()
    """
    connection_details = {}
    try:
        # Comment out if you want to prompt for an admin user credentials
        admin_user = settings.get_admin_username()
        # Comment out if you want to prompt for an admin user credentials        
        admin_password = settings.get_admin_password()
        
        # A user with more limited priviges should run the migration
        connection_details = {
            "host" : settings.get_drupal_host(),
            "user" : settings.get_drupal_username(),
            "password" : settings.get_drupal_password(),
            "drupal_db" : settings.get_drupal_database(),
            "wordpress_db" : settings.get_wordpress_database()
        }
    except AttributeError:
        print "Settings file is missing database information."

    # Create the working databases
    try:
        if admin_user is None:
            admin_user = connection_details["user"]
            admin_password = connection_details["password"]
            print "No username supplied. Will try connecting as {}".format(admin_user)

        # Connect as user with CREATE privilege to create the tables
        dbconn = Database(
            connection_details["host"],
            admin_user,
            admin_password
        )
    except OperationalError:
        print "Could not access the database. Aborting database creation."
    except Warning as warn:
        print "There were warnings. Setup may not have completed cleanly."
        print "{}".format(warn)
    except Exception as ex:
        template = "A {0} exception occured while trying to connect to the database:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print message
    else:
        continue_scipt = cleanup_database(dbconn, connection_details)
        if continue_scipt:
            continue_scipt = create_working_database(dbconn, connection_details)
        
        if continue_scipt:
            # Import data into working databases
            continue_scipt = import_source_databases(dbconn, connection_details["drupal_db"])

        if continue_scipt:            
            continue_scipt = setup_requirements(dbconn, connection_details["drupal_db"])
        
        if continue_scipt:
            print "...done"
        else: 
            print "Could not set up databases"


def create_working_database(dbconn, connection_details):
    """Builds the database setup MySQL query.
    
    Adjust privileges depending on your needs. 
    
    Returns:
        success: True unless database reports an OperationalError
    """
    # Assume success unless we get an OperationalError
    success = True
    host = str(connection_details["host"])
    user = str(connection_details["user"])
    password = str(connection_details["password"])
    drupal_db = str(connection_details["drupal_db"])
    wordpress_db = str(connection_details["wordpress_db"])
    privs = "SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER, CREATE TEMPORARY TABLES"
    
    print "Setting up working databases..."
    try:
        dbconn.query("CREATE DATABASE IF NOT EXISTS "+
            drupal_db+
            " CHARACTER SET utf8 COLLATE utf8_general_ci;")
        dbconn.query("CREATE DATABASE IF NOT EXISTS "+
            drupal_db+
            "_clean CHARACTER SET utf8 COLLATE utf8_general_ci;")
        dbconn.query("CREATE DATABASE IF NOT EXISTS "+
            wordpress_db+
            " CHARACTER SET utf8 COLLATE utf8_general_ci;")
        dbconn.query("GRANT "+privs+" ON "+drupal_db+
            ".* TO \'"+user+"\'@\'"+host+
            "\' IDENTIFIED BY \'"+password+"\';")
        dbconn.query("GRANT "+privs+" ON "+drupal_db+
            "_clean.* TO \'"+user+"\'@\'"+host+
            "\' IDENTIFIED BY \'"+password+"\';")
        dbconn.query("GRANT "+privs+" ON "+wordpress_db+
            ".* TO \'"+user+"\'@\'"+host+
            "\' IDENTIFIED BY \'"+password+"\';")
        dbconn.query("FLUSH PRIVILEGES;")                                                    
    except OperationalError:
        success = False
        print "...failed"
    except Warning as warn:
        print "Check that your database has been set up properly"
    else:
        print "...done"
    return success
    

def cleanup_database(dbconn, connection_details):
    """Remove working databases.

    Adjust privileges depending on your needs. 

    Returns:
        success: True unless database reports an OperationalError    
    """
    print "Cleaning up databases..."
    success = True    
    host = str(connection_details["host"])
    user = str(connection_details["user"])
    drupal_db = str(connection_details["drupal_db"])
    wordpress_db = str(connection_details["wordpress_db"])
    """
    try:
        print "DROP USER \'"+user+"\'@\'"+host+"\';"
        dbconn.query("DROP USER \'"+user+"\'@\'"+host+"\';")
    except Warning as warn:
        # In this case it's OK not to raise an exception on the warning
        # The table may not exist on the first run of the migration
        pass
    except OperationalError as ex:    
        print "OperationalError on the database: {}".format(ex[1])
        success = False
    """
    try:
        dbconn.query("DROP DATABASE IF EXISTS "+drupal_db+";")
    except Warning as warn:
        # In this case it's OK not to raise an exception on the warning
        # The table may not exist on the first run of the migration
        pass
    except OperationalError as ex:    
        print "OperationalError on the database: {}".format(ex[1])
        success = False
        
    try:
        dbconn.query("DROP DATABASE IF EXISTS "+drupal_db+"_clean;")
    except Warning as warn:
        # In this case it's OK not to raise an exception on the warning
        # The table may not exist on the first run of the migration
        pass
    except OperationalError as ex:    
        print "OperationalError on the database: {}".format(ex[1])
        success = False
        
    try:    
        dbconn.query("DROP DATABASE IF EXISTS "+wordpress_db+";")
    except Warning as warn:
        # In this case it's OK not to raise an exception on the warning
        # The table may not exist on the first run of the migration
        pass
    except OperationalError as ex:    
        print "OperationalError on the database: {}".format(ex[1])
        success = False
                
    if success:
        print "...done"
    else:
        print "...failed"
    return success


def import_source_databases(dbconn, database):
    """Imports source Drupal and WordPress databases.

    Two external SQL scripts are needed:
    * one to reset the Drupal database to its orginal pre-migration state;
    * one to reset the WordPress tables to a newly installed state.

    Args:
        dbconn: An open connection to the Drupal database.
        database: A selected database if not specified in script.

    Returns:
        success: True unless database reports an OperationalError        
    """
    print "Importing source databases..."    
    drupal_tables_setup_success = False
    wp_tables_setup_success = False
    
    try:
        project_path = get_default_project_path()
        drupal_db = settings.get_drupal_database()
        
        drupal_setup_file = (project_path + settings.get_drupal_setup_script())
        wordpress_setup_file = (project_path + settings.get_wordpress_setup_script())
    except AttributeError:
        print "Settings file is missing database information."

    try:
        if os.path.isfile(drupal_setup_file):
            print "Setting up Drupal content from source dump file..."
            drupal_tables_setup_success = dbconn.execute_sql_file(drupal_setup_file, database)
        else:
            print "Could not find a SQL script file to setup the Drupal tables"

        if os.path.isfile(wordpress_setup_file):
            print "Setting up a fresh WordPress tables..."
            wp_tables_setup_success = dbconn.execute_sql_file(wordpress_setup_file, database)
        else:
            print "Could not find a SQL script file to setup the WordPress tables"
    except MySQLdb.OperationalError:
        print "Could not access the database. Aborting database creation."        
        print "...failed"
    else:
        print "...done"

    if drupal_tables_setup_success:
        print "Source Drupal tables imported"
    else:
        print "Could not import srouce Drupal tables"

    if wp_tables_setup_success:
        print "WordPress export tables were created"
    else:
        print "Could not create WordPress export tables"
        
    return drupal_tables_setup_success and wp_tables_setup_success


def setup_requirements(dbconn, database=None):
    """Setup the migration requirements.

    Args:
        dbconn: An open connection to the Drupal database.
        database: The database to setup.

    Returns:
        True if setup process completed without problems

    Runs any scripts to setup migration requirements.
    """
    setup = True

    print "Setting up project requirements..."
    try:
        custom_script_path = os.path.dirname(os.path.realpath(__file__))
        custom_script = custom_script_path+os.sep+settings.get_setup_script_filename()
        custom_sql_path = settings.get_default_project_path()            
        custom_sql = custom_sql_path+os.sep+settings.get_setup_sql_filename()
    except AttributeError:
        print "Could not find custom setup script."
        setup = False            
        raise
    except Exception as ex:
        setup = False     
        raise
    else:
        if os.path.isfile(custom_sql):
            setup = dbconn.execute_sql_file(custom_sql, database)
        else:
            print "No custom setup SQL found at {}".format(custom_sql)

        if os.path.isfile(custom_script):
            print "Execute custom setup script at {}".format(custom_script)
            subprocess.check_call(["python", custom_script])
        else:
            print "No custom setup scripts found {}".format(custom_script)
            
    if setup:
        print "...done"
    else:
        print "...failed"

    return setup


def process_arguments(options):
    """Process the command line options.

    Args:
        arguments (dictionary): A dictionary of options.
    """
    # Has the user specified a path?
    try:
        run_setup(options['path'])
    except KeyError:
        print "Aborting: No project path specified"


def main(argv):
    """Process the user's commands.

    Args:
        argv: The command line options.
    """
    try:
        opts, args = getopt.getopt(
            argv,
            "p:h",
            ["path=", "help"]
        )
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)

    arguments = dict()
    # Get command line options and arguments
    if len(opts) != 0:
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print_usage()
                sys.exit()
            elif opt in ("-p", "--path"):
                arguments['path'] = arg
    else:
        arguments['path'] = get_default_project_path()

    process_arguments(arguments)


# Program entry point
if __name__ == "__main__":
    main(sys.argv[1:])
