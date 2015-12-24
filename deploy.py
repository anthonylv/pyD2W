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
    deployed = True

    try:
        custom_script_path = os.path.dirname(os.path.realpath(__file__))
        custom_script = custom_script_path+os.sep+settings['database']['deploy_script_filename']
        custom_sql = settings['database']['deploy_sql_filename']
    except AttributeError:
        print "Could not find custom deploy script."
        deployed = False            
        raise
    except Exception as ex:
        deployed = False     
        raise
    else:
        if os.path.isfile(custom_sql):
            deployed = dbconn.execute_sql_file(custom_sql, database)
        else:
            print "No custom deploy SQL found at {}".format(custom_sql)

        if os.path.isfile(custom_script):
            print "Execute custom deploy script at {}".format(custom_script)
            subprocess.check_call(["python", custom_script])
        else:
            print "No custom deploy scripts found {}".format(custom_script)
    return deployed
            
