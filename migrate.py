#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Migrate database.

This module contains the logic to run the migration.
"""

import os, subprocess
import display_cli as cli


def run_migration(settings, dbconn, database=None):
    """Migrate drupal

    Args:
        database: An open connection to the Drupal database.
        
    """
    migrated = False

    try:
        custom_sql = settings['sql']['migrate_sql_filename']
    except AttributeError:
        print "Could not find custom migrate script."
    else:
        if os.path.isfile(custom_sql):
            migrated = dbconn.execute_sql_file(custom_sql, database)
        else:
            print "No custom migrate SQL found at {}".format(custom_sql)
        #################################
        # Put any custom steps here
        #################################
        # Begin custom steps

        # End custom steps
        #################################
    return migrated
            
