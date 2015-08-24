#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Set up a Drupal to WordPress migration project.

Sets a Drupal to WordPress migration project by creating
project file folders and working databases. 
"""

import sys, getopt, os
import display_cli as cli
import settings as settings
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
        create_directory(os.path.join(path, "Custom"))
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


def create_databases():
    """Create local working databases.
    
    Create the local working databases using a user with CREATE privilege
    but assign those databases to the migration user who may have more
    limited privileges.
    """
    print "About to create working databases. Please enter credentials for a database user with CREATE privilege."
    admin_user, admin_password = cli.ask_credentials()
    
    try:
        drupal_host = settings.get_drupal_host()
        drupal_db = settings.get_drupal_database()
        drupal_user = settings.get_drupal_username()
        drupal_password = settings.get_drupal_password()        
        wordpress_db = settings.get_wordpress_database()
        
        # We need user with CREATE privilege to create the tables
        database = Database(
            drupal_host,
            admin_user,
            admin_password
        )
    except AttributeError:
        print "Settings file is missing database information."
    except OperationalError:
        print "Could not access the database. Aborting database creation."
    except Exception as ex:
        template = "A {0} exception occured while trying to connect to the database:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print message
        #TO DO: somehow handle _mysql_exceptions.OperationalError without importing MySQLdb
    else:
        try:
            # We need user with more limited priviges to run the migration
            query = build_database_setup_query(
                drupal_host,
                drupal_user,
                drupal_password,
                drupal_db,
                wordpress_db
            )
            
            print "Setting up working databases..."
            database.query(query)
            print "...done"
        except Exception as ex:
            template = "A {0} exception occured while trying to setup the databases:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            print message
            

def build_database_setup_query(host, user, password, drupal_db, wordpress_db):
    """Builds the database setup MySQL query.
    
    Adjust privileges depending on your needs. 
    """

    privs = "SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER, CREATE TEMPORARY TABLES"
    query = (
        #"CREATE USER \'"+user+"\'@\'"+host+"\' IDENTIFIED BY \'"+password+"\';"
        "CREATE DATABASE IF NOT EXISTS "+drupal_db+" CHARACTER SET utf8 COLLATE utf8_general_ci;"
        "CREATE DATABASE IF NOT EXISTS "+drupal_db+
            "_clean CHARACTER SET utf8 COLLATE utf8_general_ci;"
        "CREATE DATABASE IF NOT EXISTS "+wordpress_db+
            " CHARACTER SET utf8 COLLATE utf8_general_ci;"
        "GRANT "+privs+" ON "+drupal_db+
            ".* TO \'"+user+"\'@\'"+host+"\' IDENTIFIED BY \'"+password+"\';"
        "GRANT "+privs+" ON "+drupal_db+
            "_clean.* TO \'"+user+"\'@\'"+host+"\' IDENTIFIED BY \'"+password+"\';"
        "GRANT "+privs+" ON "+wordpress_db+
            ".* TO \'"+user+"\'@\'"+host+"\' IDENTIFIED BY \'"+password+"\';"
        "FLUSH PRIVILEGES;"
        )
    return query
    

def process_arguments(options):
    """Process the command line options.

    Args:
        arguments (dictionary): A dictionary of options.
    """
    # Has the user specified a path?
    try:
        #run_setup(options['path'])
        create_databases()
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
