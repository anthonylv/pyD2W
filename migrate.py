#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Migrate database.

This module contains the logic to run the migration.
"""

import os, subprocess
import display_cli as cli
import settings


def run_migration(database):
    """Migrate drupal

    Args:
        database: An open connection to the Drupal database.
        
    """
    try:
        custom_script_path = settings.get_default_project_path()
        custom_script = custom_script_path+os.sep+settings.get_migrate_script_filename()
        custom_sql = custom_script_path+os.sep+settings.get_migrate_sql_filename()
    except AttributeError:
        print "Could not find custom migrate script."
        raise
    except Exception as ex:
        raise
    else:
        if os.path.isfile(custom_sql):
            print "Executing custom migrate SQL at {}".format(custom_sql)
            print "Run the migration"
        else:
            print "No custom migrate SQL found at {}".format(custom_sql)
    
        if os.path.isfile(custom_script):
            print "Executing custom migrate script at {}".format(custom_script)
            subprocess.check_call(["python", custom_script])
        else:
            print "No custom migrate scripts found {}".format(custom_script)
            
