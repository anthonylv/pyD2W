#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Run utilites for a Drupal to WordPress migration.

This module is a helper utility to migrate a Drupal site to WordPress.

Usage: drupaltowordpress.py [-h --help | -a=analyse|fix|reset] [-d=database_name]

Options:
-a act, --action act
    Perform an action on the database (see Actions section below)

-d database_name, --database database_name
    Perform the action on database specified by database_name

-h, --help
    Display options

Actions:
analyse     : Analyse the Drupal database
fix         : Try to fix database problems
reset       : Reset the tables into a clean state ready for another migration pass
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
    if database.connected():
        # General analysis of Drupal database properties
        drupal_posts = database.get_drupal_posts()
        drupal_terms = database.get_drupal_terms()
        drupal_node_types = database.get_drupal_node_types()
        drupal_node_count_by_type = database.get_drupal_node_count_by_type()

        # Look for common problems
        duplicate_terms = database.get_drupal_duplicate_term_names()
        terms_exceeded_charlength = database.get_terms_exceeded_charlength()
        dupliate_alias = database.get_dupliate_alias()

        results = {
            "posts": drupal_posts,
            "terms": drupal_terms,
            "duplicate_terms": duplicate_terms,
            "node_types": drupal_node_types,
            "terms_exceeded_charlength": terms_exceeded_charlength,
            "dupliate_alias": dupliate_alias,
            "node_count_by_type": drupal_node_count_by_type
        }
        cli.print_diagnostics(results)
    else:
        print "No database connection"


def reset(database):
    """Reset the tables into a clean state ready for another migration pass.

    Args:
        database: An open connection to the Drupal database.
    """
    wp_tables_setup_success = False
    if database.connected():
        database.cleanup_tables()
        wordpress_setup_file = (os.path.dirname(os.path.realpath(__file__)) +
                                settings.get_wordpress_setup_sql_script_filename())
        if os.path.isfile(wordpress_setup_file):
            wp_tables_setup_success = database.execute_sql_file(wordpress_setup_file)
        else:
            print "Could not find a SQL script file to setup the WordPress tables"
    else:
        print "No database connection"
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
            terms_with_duplicate_names = database.get_drupal_terms_with_duplicate_names()
            fixed_term_names = processor.process_duplicate_term_names(
                terms_with_duplicate_names)
            for term in fixed_term_names:
                #result = database.insert_processed_term_names(term["tid"], term["name"])
	            #pass
                print "[{}] : {}".format(term["tid"], term["name"])
                # TO DO:
                # Compare drupal_terms_with_duplicate_names with fixed_term_names
                # Ensure tid are same
        else:
            print "No database connection"
    else:
        print "Fix process aborted"


def run_sql_script(database, filename):
    """Run a specififed mySQL script.

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
    """Run the migration script - TO BE IMPLEMENTED.

    Args:
        database: An open connection to the Drupal database.
    """
    print "This process will alter your database"
    answer = cli.query_yes_no("Are you sure you want to continue?", "no")
    if answer:
        if database.connected():
            '''
            check for problems
            if there are problems
                then prompt to run_fix()
                exit
            else
                run the migration
            '''
            print "Run the migration"
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

    # Process command line options and arguments
    if action in ['analyse', 'analyze']:
        run_diagnostics(database)
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
        print "reset() with "+selected_database
        #reset(database)
    else:
        cli.print_usage()


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


# Program entry point
if __name__ == "__main__":
    main(sys.argv[1:])
