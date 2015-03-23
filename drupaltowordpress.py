#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Run utilites for a Drupal to WordPress migration.

This module is a helper utility to migrate a Drupal site to WordPress.

Usage: drupaltowordpress.py [-h --help | -a=analyse|fix|migrate|reset|sqlscript] [-d=database_name] [-s=script_path]

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
fix         : Try to fix database problems
migrate     : Run the migration script
reset       : Reset the tables into a clean state ready for another migration pass
sqlscript   : Run the specified MySQL script file
"""

import sys, getopt, os
import display_cli as cli
import database_processor as processor
import settings as settings
from database_interface import Database

def run_diagnostics(database):
    """ Show Drupal database analysis but don't alter any Drupal CMS tables.

    Args:
        database: An open connection to the Drupal database.
    """
    results = {}
    if database.connected():
        
        check_tables(database)
        
        # General analysis of Drupal database properties
        drupal_version = database.get_drupal_version()
        drupal_posts_count = len(database.get_drupal_posts())
        drupal_terms_count = len(database.get_drupal_terms())
        drupal_node_types = database.get_drupal_node_types()
        drupal_node_types_count = len(drupal_node_types)
        drupal_node_count_by_type = database.get_drupal_node_count_by_type()

        # Look for common problems
        duplicate_terms_count = len(database.get_drupal_duplicate_term_names())
        terms_exceeded_char_count = len(database.get_terms_exceeded_charlength())
        duplicate_aliases_count = len(database.get_duplicate_aliases())

        results = {
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
    else:
        print "No database connection"
    return results


def check_tables(database):
    """Check if the required tables are present.

    Args:
        database: An open connection to the Drupal database.    
    """
    print "Checking tables..."

    tables = [
        'node',
        'node_type',
        'system',
        'term_data',
        'url_alias'
    ]

    for table in tables:
        count = database.get_table_count(table)
        if count > 0:
            print "{} exits".format(table)
        else:
            print "{} does not exist".format(table)


def reset(database):
    """Reset the tables into a clean state ready for another migration pass.

    Two external SQL scripts are needed:
    * one to reset the Drupal database to its orginal pre-migration state;
    * one to reset the WordPress tables to a newly installed state.

    Args:
        database: An open connection to the Drupal database.
    """
    drupal_tables_setup_success = False
    wp_tables_setup_success = False
    if database.connected():
        database.cleanup_tables()

        drupal_setup_file = (os.path.dirname(
            os.path.realpath(__file__)) + settings.get_drupal_setup_script())
        wordpress_setup_file = (os.path.dirname(
            os.path.realpath(__file__)) + settings.get_wordpress_setup_script())
        if os.path.isfile(drupal_setup_file):
            drupal_tables_setup_success = database.execute_sql_file(drupal_setup_file)
        else:
            print "Could not find a SQL script file to setup the WordPress tables"

        if os.path.isfile(wordpress_setup_file):
            wp_tables_setup_success = database.execute_sql_file(wordpress_setup_file)
        else:
            print "Could not find a SQL script file to setup the WordPress tables"
    else:
        print "No database connection"

    if drupal_tables_setup_success:
        print "Drupal tables reset to a clean state"
    else:
        print "Could not reset Drupal tables to a clean state"

    if wp_tables_setup_success:
        print "WordPress export tables were created"
    else:
        print "Could not create WordPress export tables"


def run_fix(database):
    """Try to fix any issues that would cause the migration to fail.

    Args:
        database: An open connection to the Drupal database.
    """
    print "This process will alter your database"
    answer = cli.query_yes_no("Are you sure you want to continue?", "no")
    if answer:
        if database.connected():
            # Warning: this may push the name length past WordPress' 200 char limit
            terms_with_duplicate_names = database.get_drupal_duplicate_terms()
            fixed_term_names = processor.process_duplicate_term_names(
                terms_with_duplicate_names)
            for term in fixed_term_names:
                database.update_processed_term_name(term["tid"], term["name"])
            # Warning: this may undo duplicates fix if the term was close to the 200 char limit
            database.update_term_name_length()
            database.uniquify_url_aliases()
            print "Fix complete"
        else:
            print "No database connection"
    else:
        print "Fix process aborted"


def run_sql_script(database, filename):
    """Run a specified mySQL script.

    Args:
        database: An open connection to the Drupal database.
        filename: Filename with full path to the script.
    """
    if os.path.isfile(filename):
        print "You are about to run a script that may alter your database"
        answer = cli.query_yes_no("Are you sure you want to continue?", "no")
        if answer:
            if database.connected():
                database.execute_sql_file(filename)
            else:
                print "No database connection"
        else:
            print "Script aborted"
    else:
        print "No script file found at: "+filename


def migrate(database):
    """Run the migration script.

    Args:
        database: An open connection to the Drupal database.
    """
    print "The migration process will alter your database"
    answer = cli.query_yes_no("Are you sure you want to continue?", "no")
    if answer:
        if database.connected():
            diagnostic_results = run_diagnostics(database)
            duplicate_terms_count = diagnostic_results["duplicate_terms_count"]
            terms_exceeded_char_count = diagnostic_results["terms_exceeded_char_count"]
            duplicate_aliases_count = diagnostic_results["duplicate_aliases_count"]

            if (duplicate_terms_count > 0 or
                    terms_exceeded_char_count > 0 or
                    duplicate_aliases_count > 0):
                print "There are problems that must be fixed before migrating."
                run_fix(database)
                print "Please re-run '-a migrate' to continue with the migration."
            else:
                standard_migration_file = (os.path.dirname(
                    os.path.realpath(__file__)) + settings.get_migration_script())
                if os.path.isfile(standard_migration_file):
                    database.execute_sql_file(standard_migration_file)
                else:
                    print "Could not find the migration script at "+standard_migration_file
        else:
            print "No database connection"
    else:
        print "Migration aborted"


def process_action(action, options):
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
        selected_database = settings.get_drupal_database()

    database = Database(
        settings.get_drupal_host(),
        settings.get_drupal_username(),
        settings.get_drupal_password(),
        selected_database
    )

    if database.connected():
        # Process command line options and arguments
        if action in ['analyse', 'analyze']:
            cli.print_diagnostics_header()
            diagnostics_results = run_diagnostics(database)
            cli.print_diagnostics(diagnostics_results)
        elif action == 'fix':
            run_fix(database)
        elif action == 'migrate':
            migrate(database)
        elif action == 'sqlscript':
            # Has the user specified a sql script?
            if 'script_option' in options:
                run_sql_script(database, options['script_option'])
            else:
                print "You need to provide a path to the script."
                cli.print_usage()
        elif action == "reset":
            reset(database)
        else:
            cli.print_usage()
    else:
        print "No database connection"

def main(argv):
    """Process the user's commands.

    Args:
        argv: The command line options.
    """
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
        process_action(action, options)
    else:
        print "You need to specify an action to perform or use -h flag to view usage instructions."


# Program entry point
if __name__ == "__main__":
    main(sys.argv[1:])
