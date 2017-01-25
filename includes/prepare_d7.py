#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Prepare the working database.

This module contains the logic to prepare the working database for
a run through of the migration scripts.

Support for Drupal 7
"""

from MySQLdb import OperationalError
from d2w import run_sql_script
import os, subprocess
import display_cli as cli


def prepare_migration(settings, dbconn, database=None):
    """Prepare the working database.

    Args:
        dbconn: An open connection to the Drupal database.
        database: The database to prepare.
        
    Returns:
        True if prepare process completed without problems
        
    Tries to fix any issues in the database and runs any
    custom MySQL and Python scripts in the project directory
    """
    prepared = True
    fixed = run_fix(dbconn)

    if fixed:
        try:
            custom_sql = settings['sql']['prepare_sql_filename']
        except AttributeError:
            print "Could not find custom prepare script."
        else:
            if os.path.isfile(custom_sql):
                prepared = dbconn.execute_sql_file(custom_sql, database)
            else:
                print "No custom prepare SQL found at {}".format(custom_sql)
            #################################
            # Put any custom steps here
            #################################
            # Begin custom steps

            # End custom steps
            #################################
    else:
        print "Aborted database preparation. There were problems that couldn't be fixed."
        prepared = False

    return prepared
        


def run_fix(dbconn):
    """Try to fix any issues that would cause the migration to fail.

    Args:
        dbconn: An open connection to the Drupal database.
        
    Returns:
        True if completed all the fixer processes
    """
    success = False
    print "Trying to fix any issues that would cause the migration to fail."
    try:
        # Warning: this may push the name length past WordPress' 200 char limit
        terms_with_duplicate_names = dbconn.get_drupal_duplicate_terms()
        fixed_term_names = process_duplicate_term_names(
            terms_with_duplicate_names
        )
        for term in fixed_term_names:
            update_processed_term_name(dbconn, term["tid"], term["name"])
        # Warning: this may undo duplicates fix if the term was close to the 200 char limit
        update_term_name_length(dbconn)
        success = uniquify_url_aliases(dbconn)
    except OperationalError:
        print "Could not access the database. Aborting attempt to fix database."
    except Warning as warn:
        print "There were warnings. Fix may not have completed cleanly."
        print "{}".format(warn)
    except Exception as ex:
        template = "A {0} exception occured while trying to fix the database:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print message

    if success:
        print "Fix complete"
    return success


def process_duplicate_term_names(duplicate_term_names):
    """Create unique term names by appending the term id.

    Args:
        drupal_terms_with_duplicate_names (list): A list of Drupal terms.

    Returns:
        updated_terms (list): A list of Drupal terms comaptible with WordPress.
    """
    print "Processing duplicate term names"
    updated_terms = list()
    duplicate_terms_count = len(duplicate_term_names)
    if duplicate_terms_count > 0:
        print "Creating unique term names by appending the term id..."
        for term in duplicate_term_names:
            term_attributes_list = {'tid': term["tid"], 'name': term["name"]+"_"+str(term["tid"])}
            print "tid {}: {}".format(term_attributes_list["tid"], term_attributes_list["name"])
            updated_terms.append(term_attributes_list)
    else:
        print "No duplicate term names"
    return updated_terms
    

def create_working_tables(dbconn):
    """Create some working tables to hold temporary data.

    This function creates working tables useful for debugging migration problems.

    Args:
        dbconn: An open connection to the Drupal database.    
    """
    print "Creating working tables"
    dbconn.query("CREATE TABLE IF NOT EXISTS acc_fixed_term_names ( \
                    tid INT(10) NOT NULL UNIQUE, name VARCHAR(255)) ENGINE=INNODB;")


def uniquify_url_aliases(dbconn):
    """Remove duplicate aliases but keep a copy in a working table.

    URL alias will be used as the WordPress post slug but these need to be unique.
    Create a url_alias table of unique aliases and keep a copy of the original
    for later processing.
    """
    success = True
    print "Uniquifing URL aliases"
    try:
        dbconn.query("DROP TABLE IF EXISTS acc_url_alias_dups_removed;")
    except Warning as warn:
        # In this case it's OK not to raise an exception on the warning
        # The table may not exist on the first run of the migration
        pass

    try:
        dbconn.query("DROP TABLE IF EXISTS acc_url_alias_with_dups;")
    except Warning as warn:
        # In this case it's OK not to raise an exception on the warning
        # The table may not exist on the first run of the migration
        pass

    try:
        dbconn.query("CREATE TABLE acc_url_alias_dups_removed \
                    AS SELECT pid, source, alias FROM url_alias GROUP BY source;")
    except Warning as warn:
        print "There were warnings. Fix may not have completed cleanly."
        print "{}".format(warn)
        success = False        

    try:
        dbconn.query("RENAME TABLE url_alias TO acc_url_alias_with_dups;")
    except Warning as warn:
        print "There were warnings. Fix may not have completed cleanly."
        print "{}".format(warn)
        success = False
                
    try:    
        dbconn.query("RENAME TABLE acc_url_alias_dups_removed TO url_alias;")
    except Warning as warn:
        print "There were warnings. Fix may not have completed cleanly."
        print "{}".format(warn)
        success = False

    return success


def update_processed_term_name(dbconn, tid, name):
    """Insert term names that have been processed to meet WordPress' criteria.

    Args:
        tid (integer): The Drupal taxonomy ID.
        name (string): The Drupal taxonomy name.
    """
    query = "UPDATE taxonomy_term_data SET name='"+name+"' WHERE tid="+str(tid)+";"
    return dbconn.insert(query)


def update_term_name_length(dbconn):
    """Truncate term name to fit WordPress' 200 character limit
    """
    dbconn.query("UPDATE taxonomy_term_data SET name=SUBSTRING(name, 1, 200);")


