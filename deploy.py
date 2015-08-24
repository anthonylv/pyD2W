#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Deploy the database.

This module contains the logic to deploy the database
to the staging server
"""

import os, subprocess
import settings


def deploy_database(database):
    """Deploy the database

    Args:
        database: An open connection to the Drupal database.
    
    Deploy the database tables into the staging server.
    """
    try:
        custom_script_path = settings.get_default_project_path()
        custom_script = custom_script_path+os.sep+settings.get_deploy_script_filename()
        custom_sql = custom_script_path+os.sep+settings.get_deploy_sql_filename()
    except AttributeError:
        print "Could not find custom deploy script."
        raise
    except Exception as ex:
        raise
    else:
        if os.path.isfile(custom_sql):
            print "Executing custom deploy SQL at {}".format(custom_sql)
        else:
            print "No custom deploy SQL found at {}".format(custom_sql)
    
        if os.path.isfile(custom_script):
            print "Executing custom deploy script at {}".format(custom_script)
            subprocess.check_call(["python", custom_script])
        else:
            print "No custom deploy scripts found {}".format(custom_script)