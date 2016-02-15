#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Deploy the database.

This module contains the logic to deploy the database
to the staging server
"""

import os, subprocess

def deploy_database(settings, dbconn, database=None):
    """Deploy the database

    Args:
        database: An open connection to the Drupal database.
    
    Deploy the database tables into the staging server.
    """
    deployed = False

    try:
        custom_sql = settings['sql']['deploy_sql_filename']
    except AttributeError:
        print "Could not find custom deploy script."
    else:
        if os.path.isfile(custom_sql):
            deployed = dbconn.execute_sql_file(custom_sql, database)
        else:
            print "No custom deploy SQL found at {}".format(custom_sql)
        #################################
        # Put any custom steps here
        #################################
        # Begin custom steps

        # End custom steps
        #################################
    return deployed
            
