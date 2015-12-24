#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Set up a Drupal to WordPress migration project.

Sets a Drupal to WordPress migration project by creating
project file folders and working databases. 
"""

import sys, getopt, os
import logging, logging.handlers
import yaml
from datetime import datetime
import display_cli as cli
from os.path import expanduser
from database_interface import Database
from MySQLdb import OperationalError
from subprocess import check_call

logger = logging.getLogger()


def setup_logging(settings):
    """Log output

        Sends log output to console or file,
        depending on error level
    """
    try:
        log_filename = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            settings['log_filename']
        )
        log_max_bytes = settings['log_max_bytes']
        log_backup_count = settings['log_backup_count']
    except KeyError as ex:
        print "WARNING: Missing logfile setting {}. Using defaults.".format(ex)
        log_filename = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "log.txt"
        )
        log_max_bytes = 1048576 #1MB
        log_backup_count = 5

    logger.setLevel(logging.DEBUG)
    # Set up logging to file
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_filename,
        maxBytes=log_max_bytes,
        backupCount=log_backup_count
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s %(name)-15s %(levelname)-8s %(message)s',
        '%m-%d %H:%M'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Handler to write INFO messages or higher to sys.stderr
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('...%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    logger.debug("---------------------------------")
    logger.debug(
        "Starting log for session %s",
        datetime.now().strftime("%Y%m%d%H%M%S%f")
    )


def get_settings():
    """Get settings from external YAML file
    """
    settings = {}
    settings_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "settings.yml"
    )
    try:
        with open(settings_file, 'r') as ymlfile:
            settings = yaml.load(ymlfile)
    except IOError:
        logger.error("Could not open settings file")
    else:
        logger.debug("Opened settings file")
    return settings


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
        logger.info("Creating project directories.")
        create_directory(path)
        create_directory(os.path.join(path, "Analysis"))
        create_directory(os.path.join(path, "Archives"))
        create_directory(os.path.join(path, "Exports"))
        create_directory(os.path.join(path, "Specifications"))
        create_directory(os.path.join(path, "SQL"))
        logger.info("Setting up databases.")
        setup_databases()
        show_instructions()
    else:
        print "Project setup aborted"


def show_instructions():
    print ("Setup is complete. "
        "Remember to copy over the migration files into your project directory:\n"
        "* prepare.sql\n"
        "* migrate-xx.sql\n"
        "* deploy.sql"
    )


def get_default_project_path():
    """Gets the default project path.

    Returns:
        Path to the project directory
    """    
    settings = get_settings()
    project_path = os.getcwd()+os.sep+"new_project"
    try:
        project_path = settings['project']['default_project_path']
    except KeyError:
        logger.info(
            "Settings file does not have a default project path."
            "Using default: %s",
            project_path
        )
        raise
    return project_path
    

def create_directory(path):
    """Create a directory.
    
    Args:
        path: Path to the project location.    
    """
    logger.debug("Creating directory: %s", path)
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as e:
            logger.error(
                "Sorry there was a problem creating the directory: %s",
                e.strerror
            )            
            if not path:
                logger.error("The path string is empty")
    else:
        logger.debug("The directory %s already exists", path)


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
    print (
        "About to create working databases. "
        "Please enter credentials for a database user with CREATE privilege."
    )
    # We need a user with CREATE privilege to create the tables
    admin_user, admin_password = cli.ask_credentials()
    """
    settings = get_settings()
    connection_details = {}
    
    try:
        # Comment out if you want to prompt for an admin user credentials
        admin_user = settings['database']['admin_username']
        # Comment out if you want to prompt for an admin user credentials 
        admin_password = settings['database']['admin_password']
        
        # A user with more limited priviges should run the migration
        connection_details = {
            "host" : settings['database']['drupal_host'],
            "user" : settings['database']['drupal_username'],
            "password" : settings['database']['drupal_password'],
            "drupal_db" : settings['database']['drupal_database'],
            "wordpress_db" : settings['database']['wordpress_database']
        }
    except AttributeError:
        logger.error("Settings file is missing database information.")

    # Create the working databases
    try:
        if admin_user is None:
            admin_user = connection_details["user"]
            admin_password = connection_details["password"]
            logger.error(
                "No username supplied. Will try connecting as %s",
                admin_user
            )

        # Connect as user with CREATE privilege to create the tables
        dbconn = Database(
            connection_details["host"],
            admin_user,
            admin_password
        )
    except OperationalError:
        logger.error(
            "Could not access the database. Aborting database creation."
        )
    except Warning as warn:
        logger.warning(
            "There were warnings. Setup may not have completed cleanly.\n"
            "Warning: %s",
            warn
        )
    except Exception as ex:
        template = "A {0} exception occured while trying to connect to the database:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logger.error(message)
    else:
        continue_scipt = cleanup_database(dbconn, connection_details)
        if continue_scipt:
            continue_scipt = create_working_database(
                dbconn,
                connection_details
            )
        
        if continue_scipt:
            # Import data into working databases
            drupal_setup_success, wp_setup_success = import_source_databases(
                dbconn,
                connection_details["drupal_db"]
            )

        # Drupal databases may take a long time to import.
        # Allow setup script to continue even if Drupal tables
        # haven't been setup.
        if wp_setup_success:  
            continue_scipt = setup_requirements(
                dbconn,
                connection_details["drupal_db"]
            )
        
        if continue_scipt:
            logger.info("Database setup complete")
        else: 
            logger.error("Could not set up databases")


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
    privs = "SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER, CREATE TEMPORARY TABLES, LOCK TABLES"
    
    logger.debug("Setting up working databases.")
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
        dbconn.query("GRANT "+privs+" ON "+wordpress_db+
            ".* TO \'"+user+"\'@\'"+host+
            "\' IDENTIFIED BY \'"+password+"\';")
        dbconn.query("FLUSH PRIVILEGES;") 
    except OperationalError:
        success = False
        logger.error("Failed to create working databases.")
    except Warning as warn:
        logger.warning(
            "There were warnings. "
            "Check that your database has been set up properly.")
    else:
        logger.debug("Working databaes created.")
    return success
    

def cleanup_database(dbconn, connection_details):
    """Remove working databases.

    Adjust privileges depending on your needs. 

    Returns:
        success: True unless database reports an OperationalError    
    """
    logger.debug("Cleaning up databases.")
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
        logger.error("OperationalError on the database: %s", ex[1])
        success = False
    else:
        logger.debug("Dropped database %s", drupal_db)
        
    try:    
        dbconn.query("DROP DATABASE IF EXISTS "+wordpress_db+";")
    except Warning as warn:
        # In this case it's OK not to raise an exception on the warning
        # The table may not exist on the first run of the migration
        pass
    except OperationalError as ex:    
        logger.error("OperationalError on the database: %s", ex[1])
        success = False
    else:
        logger.debug("Dropped database %s", wordpress_db)
                
    if success:
        logger.debug("Database cleanup complete")
    else:
        logger.warning("Failed to cleanup database")
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
    logger.debug("Importing source databases")    
    drupal_tables_setup_success = False
    wp_tables_setup_success = False
    drupal_db = "" 
    drupal_setup_file = ""
    wordpress_setup_file = "" 
   
    try:
        settings = get_settings()
        drupal_db = settings['database']['drupal_database']
        drupal_setup_file = settings['sql']['drupal_setup_script']
        wordpress_setup_file = settings['sql']['wordpress_setup_script']
    except KeyError as ex:
        logger.warning(
            "Settings file is missing database information: %s",
            ex
        )
        raise

    try:
        if os.path.isfile(drupal_setup_file):
            logger.debug("Setting up Drupal content from source dump file.")
            drupal_tables_setup_success = dbconn.execute_sql_file(
                drupal_setup_file,
                database
            )
        else:
            # For large sites, the Drupal data will take a long time to import
            # You might want to use another method to import the data
            logger.warning(
                "Could not find a SQL script file to setup the Drupal tables. "
                "Import the Drupal data after setup."
            )
            drupal_tables_setup_success = False 
            

        if os.path.isfile(wordpress_setup_file):
            logger.debug("Setting up a fresh WordPress tables.")
            wp_tables_setup_success = dbconn.execute_sql_file(
                wordpress_setup_file,
                database
            )
        else:
            logger.warning(
                "Could not find a SQL script file to setup the WordPress tables"
            )
    except OperationalError:
        logger.error(
            "Could not access the database. Aborting database creation."
        )
        logger.error("Failed to import source database.")
    except KeyboardInterrupt:
        logger.debug("Import aborted")

    if drupal_tables_setup_success:
        logger.info("Source Drupal tables imported.")
    else:
        logger.debug("Could not import source Drupal tables")

    if wp_tables_setup_success:
        logger.info("WordPress export tables were created.")
    else:
        logger.debug("Could not create WordPress export tables.")
        
    return drupal_tables_setup_success, wp_tables_setup_success


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
    settings = get_settings()
    logger.debug("Setting up project requirements.")
    try:
        custom_script_path = os.path.dirname(os.path.realpath(__file__))
        custom_script = custom_script_path+ \
            os.sep+ \
            settings['custom_scripts']['setup_script_filename']
        custom_sql = settings['sql']['setup_sql_filename']
    except KeyError:
        logger.error("Could not find custom setup script.")
        setup = False            
        raise
    except Exception as ex:
        setup = False     
        raise
    else:
        if os.path.isfile(custom_sql):
            setup = dbconn.execute_sql_file(custom_sql, database)
        else:
            logger.debug("No custom setup SQL found at %s", custom_sql)

        if os.path.isfile(custom_script):
            logger.info("Execute custom setup script at %s", custom_script)
            check_call(["python", custom_script])
        else:
            logger.debug("No custom setup scripts found %s", custom_script)
            
    if setup:
        logger.info("Project requirements setup complete.")
    else:
        logger.error("Project requirements failed.")

    return setup


def process_arguments(options):
    """Process the command line options.

    Args:
        arguments (dictionary): A dictionary of options.
    """
    # Has the user specified a path?
    
    try:
        run_setup(options['path'])
    except KeyError as ex:
        logger.error("Aborting: missing setup option [%s]", ex)


def main(argv):
    """Process the user's commands.

    Args:
        argv: The command line options.
    """
    settings = get_settings()
    setup_logging(settings['d2w'])

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
