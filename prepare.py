#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Prepare the working database.

This module contains the logic to prepare the working database for a
run through of the migration scripts
"""

from MySQLdb import OperationalError
import os, subprocess
import display_cli as cli
import settings

def prepare_migration(database):
    """Prepare the working database.

    Args:
        database: An open connection to the Drupal database.
        
    Tries to fix any issues in the database and runs any
    custom MySQL and Python scripts in the project directory
    """
    run_fix(database)

    try:
        custom_script_path = settings.get_default_project_path()
        custom_script = custom_script_path+os.sep+settings.get_prepare_script_filename()
        custom_sql = custom_script_path+os.sep+settings.get_prepare_sql_filename()
    except AttributeError:
        print "Could not find custom prepare script."
        raise
    except Exception as ex:
        raise
    else:
        if os.path.isfile(custom_sql):
            print "Executing custom prepare SQL at {}".format(custom_sql)
        else:
            print "No custom prepare SQL found at {}".format(custom_sql)
    
        if os.path.isfile(custom_script):
            print "Executing custom prepare script at {}".format(custom_script)
            subprocess.check_call(["python", custom_script])
        else:
            print "No custom prepare scripts found {}".format(custom_script)


def run_fix(database):
    """Try to fix any issues that would cause the migration to fail.

    Args:
        database: An open connection to the Drupal database.
    """
    print "Trying to fix any issues that would cause the migration to fail."
    print "This process will alter your database {}".format(database.get_database())
    answer = cli.query_yes_no("Are you sure you want to continue?", "no")
    if answer:
        try:
            # Warning: this may push the name length past WordPress' 200 char limit
            terms_with_duplicate_names = database.get_drupal_duplicate_terms()
            fixed_term_names = process_duplicate_term_names(
                terms_with_duplicate_names)
            for term in fixed_term_names:
                database.update_processed_term_name(term["tid"], term["name"])
            # Warning: this may undo duplicates fix if the term was close to the 200 char limit
            database.update_term_name_length()
            database.uniquify_url_aliases()
            print "Fix complete"
        except OperationalError:
            print "Could not access the database. Aborting attempt to fix database."
        except Exception as ex:
            template = "A {0} exception occured while trying to fix the database:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            print message
    else:
        print "Fix process aborted"



def process_duplicate_term_names(duplicate_term_names):
    """Create unique term names by appending the term id.

    Args:
        drupal_terms_with_duplicate_names (list): A list of Drupal terms.

    Returns:
        updated_terms (list): A list of Drupal terms comaptible with WordPress.
    """
    updated_terms = list()
    duplicate_terms_count = len(duplicate_term_names)
    if duplicate_terms_count > 0:
        for term in duplicate_term_names:
            term_attributes_list = {'tid': term["tid"], 'name': term["name"]+"_"+str(term["tid"])}
            updated_terms.append(term_attributes_list)
    return updated_terms
