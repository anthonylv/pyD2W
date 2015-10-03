#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Store general settings for the application.

Since we can't have constants, use getter functions to return settings.
"""

def get_drupal_host():
    return ""

def get_drupal_username():
    return ""
 
def get_drupal_password():
    return ""
    
def get_drupal_database():
    return ""
    
def get_wordpress_host():
    return ""
    
def get_wordpress_useraname():
    return ""
    
def get_wordpress_password():
    return ""
    
def get_wordpress_database():
    return ""
    
# A user with CREATE privilege to create the tables
def get_admin_username():
    return ""

def get_admin_password():
    return ""

def get_default_project_path():
    """Get default project path.

    The directory where you'll store the project files for this migration.
    """
    return ""

def get_wordpress_setup_script():
    """Get SQL dumpfile used to setup fresh WordPress tables.

    This will normally be the database dump of a fresh WordPress installation.
    It is not expected to change across different migration projects.
    """
    return ""

def get_drupal_setup_script():
    """Get SQL dumpfile used to setup fresh Drupal tables.

    This will be the database dump of the client's Drupal installation.
    Each migration project will have a specific dump file.
    """
    return ""

def get_setup_sql_filename():
    """Filename for your setup queries.

    An SQL script containing any custom setup queries.
    """
    return ""

def get_prepare_sql_filename():
    """Filename for your prepare queries.

    An SQL script containing any custom preparation queries.
    """
    return ""

def get_migrate_sql_filename():
    """Filename for your migration queries.

    The standard migration SQL script may not work on all Drupal configurations.
    """
    return ""

def get_deploy_sql_filename():
    """Filename for your deploy quries.

    An SQL script containing any custom deployment queries.
    """
    return ""


############################################################
# Python scripts for any custom migration logic
# Place these in your pyD2W installation directory
############################################################
def get_setup_script_filename():
    """Filename for your setup script.

    A Python script containing any custom setup logic.
    """
    return ""
    
def get_deploy_script_filename():
    """Filename for your deploy script.

    A Python script containing any custom deployment logic.
    """
    return ""

def get_prepare_script_filename():
    """Filename for your prepare script.

    A Python script containing any custom preparation logic.
    """
    return ""

def get_migrate_script_filename():
    """Filename for your migration script.

    A Python script containing any custom migration logic.
    """
    return ""
