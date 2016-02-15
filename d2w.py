#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run utilites for a Drupal to WordPress migration.

This module is a helper utility to migrate a Drupal site to WordPress.

Usage: drupaltowordpress.py [-h --help | -a=analyse|migrate|reset|sqlscript] [-d=database_name] [-s=script_path]

Options:
-a act, --action act
    Perform an action on the database (see Actions section below)

-d database_name, --database database_name
    Perform the action on database specified by database_name

-s script_path, --sqlscript script_path
    Run a MySQL script file specified by script_path

-h, --help
    Display options

Actions:
analyse     : Analyse the Drupal database
migrate     : Run the migration script
sqlscript   : Run the specified MySQL script file
"""

import sys, getopt, os
import logging, logging.handlers
import yaml
from datetime import datetime
import display_cli as cli
import prepare, migrate, deploy
from database_interface import Database
from MySQLdb import OperationalError

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
    console_formatter = logging.Formatter('%(levelname)-8s %(message)s')
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


def run_diagnostics(settings, database=None):
    """ Show Drupal database analysis but don't alter any Drupal CMS tables.

    Args:
        database: The Drupal database to analyse.
    """
    results = {}
    
    try:
        if not database:
            database = settings['database']['drupal_database']

        dbconn = Database(
            settings['database']['drupal_host'],
            settings['database']['drupal_username'],
            settings['database']['drupal_password'],
            database
        )
    except AttributeError:
        logging.error("Settings file is missing database information.") 
    except OperationalError:
        logging.error(
            "Could not access the database. "
            "Aborting database creation."
        )
    else:
        try:
            drupal_version = dbconn.get_drupal_version()
        except OperationalError:
            drupal_version = None
            logging.warning(
                "Could not get Drupal version."
            )
            
        if drupal_version:
            logging.debug("Checking tables...")
            all_tables_present = check_tables(dbconn, float(drupal_version))
        else:
            drupal_version = "Unknown"
            logging.error(
                "Could not check tables since the Drupal version is unknown.")

        try:
            # General analysis of Drupal database properties
            drupal_sitename = dbconn.get_drupal_sitename()
            drupal_posts_count = len(dbconn.get_drupal_posts())
            drupal_terms_count = len(dbconn.get_drupal_terms())
            drupal_node_types = dbconn.get_drupal_node_types()
            drupal_node_types_count = len(drupal_node_types)
            drupal_node_count_by_type = dbconn.get_drupal_node_count_by_type()
            logging.debug("Looking for common problems")
            # Look for common problems
            duplicate_terms_count = len(dbconn.get_drupal_duplicate_term_names())
            terms_exceeded_char_count = len(dbconn.get_terms_exceeded_charlength())
            duplicate_aliases_count = len(dbconn.get_duplicate_aliases())
        except Exception as ex:
            logging.error(
                "Could not run diagnostics. Please use a database interface "
                "that supports Drupal version %s.",
                drupal_version
            )
        else:
            results = {
                "sitename": drupal_sitename,
                "version": drupal_version,
                "posts_count": drupal_posts_count,
                "terms_count": drupal_terms_count,
                "duplicate_terms_count": duplicate_terms_count,
                "node_types_count": drupal_node_types_count,
                "node_types": drupal_node_types,
                "terms_exceeded_char_count": terms_exceeded_char_count,
                "duplicate_aliases_count": duplicate_aliases_count,
                "node_count_by_type": drupal_node_count_by_type
            }
    return results


def check_tables(dbconn, drupal_version):
    """Check if the required tables are present.

    Args:
        dbconn: An open connection to the Drupal database.

    Returns:
        boolean: True if all required tables are present, False otherwise.
    """
    all_tables_present = True
    
    tables_d6 = [
        'comments',
        'node',
        'node_revisions',
        'node_type',
        'system',
        'term_data',
        'term_node',
        'url_alias',
        'users',
        'users_roles',
        'variable'
    ]
    
    tables_d7 = [
        'comment',
        'node',
        'node_revision',
        'node_type',
        'system',
        'taxonomy_term_data',
        'taxonomy_index',
        'url_alias',
        'users',
        'users_roles',
        'variable'
    ]    

    if drupal_version < 7.0:
        logging.debug("Using D6 tables")
        tables = tables_d6
    else:
        logging.debug("Using D7 tables")
        tables = tables_d7

    for table in tables:
        count = dbconn.get_table_count(table)
        if count > 0:
            print "...{} table exists".format(table)
        else:
            print "...{} table does not exist".format(table)
            all_tables_present = False
    return all_tables_present


def run_sql_script(settings, filename, database=None):
    """Run a specified mySQL script.

    Args:
        dbconn: An open connection to the Drupal database.
        filename: Filename with full path to the script.
    
    Returns:
        True if the file was executed.
    """
    result = False
    if not database:
        database = settings['database']['drupal_database']
    
    try:
        dbconn = Database(
            settings['database']['drupal_host'],
            settings['database']['drupal_username'],
            settings['database']['drupal_password'],
            database
        )
    except AttributeError:
        logging.error("Settings file is missing database information.") 
    except OperationalError:
        logging.error(
            "Could not access the database. "
            "Aborting database creation."
        )
    else:    
        if os.path.isfile(filename):
            if dbconn.connected():
                result = dbconn.execute_sql_file(filename, database)
            else:
                logging.error("No database connection")
        else:
            logging.error("No script file found at: %s", filename)
    return result


def process_migration(settings, database=None):
    # Continue unless something happens to abort process
    continue_script = True
    print "The migration process will alter your database"
    continue_script = cli.query_yes_no("Are you sure you want to continue?", "no")
        
    if continue_script:
        try:
            if not database:
                database = settings['database']['drupal_database']

            dbconn = Database(
                settings['database']['drupal_host'],
                settings['database']['drupal_username'],
                settings['database']['drupal_password'],
                database
            )
        except AttributeError:
            logger.error("Settings file is missing database information.") 
        except OperationalError:
            logger.error(
                "Could not access the database. Aborting database creation."
            )
        else:
            cli.print_header("Preparing {} for migration".format(database))
            continue_script = prepare.prepare_migration(settings, dbconn, database)
            
    if continue_script:
        if check_migration_prerequisites(settings, dbconn, database):
            cli.print_header("Migrating content from {}".format(database))
            continue_script = migrate.run_migration(settings, dbconn, database)
        else:
            logging.critical(
                "Migration aborted because it did not meet "
                "the prerequistes for success."
            )

    if continue_script:
        cli.print_header("Deploying to test environment")
        continue_script = deploy.deploy_database(settings, dbconn, database)

    if not continue_script:
        sys.exit(1)


def check_migration_prerequisites(settings, dbconn, database=None):
    """Run the migration script.

    Args:
        dbconn: An open connection to the Drupal database.
        
    Returns:
        True if OK to proceed; False if migration should be aborted.
    """
    print "Checking migration prerequisites..."
    custom_sql_exists = False
    custom_script_exists = False
    success = False
    if dbconn.connected():
        diagnostic_results = run_diagnostics(settings, database)
        duplicate_terms_count = diagnostic_results["duplicate_terms_count"]
        terms_exceeded_char_count = diagnostic_results["terms_exceeded_char_count"]
        duplicate_aliases_count = diagnostic_results["duplicate_aliases_count"]

        if (duplicate_terms_count > 0 or
                terms_exceeded_char_count > 0 or
                duplicate_aliases_count > 0):
            print "There are problems that must be fixed before migrating"
            print "Please re-run '-a migrate' to continue with the migration"
        else:
            logger.info("Common migration problems fixed")
            success = True
    else:
        logger.error("No database connection")

    if success:
        logger.info("OK to proceed with migration")
    else:
        logger.error("Cannot proceed with migration")
    return success


def process_action(settings, action, options):
    """Process the command line options.

    Args:
        action (string): A string containing the action to run.
        options (dictionary): A dictionary of options.
    """
    # Has the user specified a database? Use default in settings file if not
    selected_database = None
    if 'db_option' in options:
        selected_database = options['db_option']
    else:
        selected_database = None

    # Process command line options and arguments
    if action in ['analyse', 'analyze']:
        cli.print_header("Starting Drupal To WordPress diagnostics")
        diagnostics_results = run_diagnostics(settings, selected_database)
        if diagnostics_results:
            cli.print_diagnostics(diagnostics_results)
    elif action == 'migrate':
        process_migration(settings, selected_database)
    elif action == 'sqlscript':
        # Has the user specified a sql script?
        if 'script_option' in options:
            run_sql_script(settings, options['script_option'], selected_database)
        else:
            print "You need to provide a path to the script."
            cli.print_usage()
    else:
        cli.print_usage()


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
            "a:d:s:h",
            ["action=", "database=", "script=", "help"]
        )
    except getopt.GetoptError:
        cli.print_usage()
        sys.exit(2)

    action = None
    options = dict()
    # Get command line options and arguments
    if len(opts) == 0:
        cli.print_usage()
    else:
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                cli.print_usage()
                sys.exit()
            elif opt in ("-d", "--database"):
                options['db_option'] = arg
            elif opt in ("-s", "--sqlscript"):
                options['script_option'] = arg
            elif opt in ("-a", "--action"):
                action = arg
    # Only process actions after getting all the specified options
    if action:
        process_action(settings, action, options)
    else:
        print (
            "You need to specify an action to perform "
            "or use -h flag to view usage instructions."
        )

# Program entry point
if __name__ == "__main__":
    main(sys.argv[1:])
