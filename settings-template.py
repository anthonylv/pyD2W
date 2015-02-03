#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Store general settings for the application.

Since we can't have constants, use getter functions to return settings.
"""

def get_drupal_host():
    return "127.0.0.1"
    
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

def get_wordpress_setup_script():
    """Get SQL dumpfile used to setup fresh WordPress tables.

    This will normally be the database dump of a fresh WordPress installation.
    It is not expected to change across different migration projects.
    """
    return "/sql/create_tables_wordpress35-v2.sql"

def get_drupal_setup_script():
    """Get SQL dumpfile used to setup fresh Drupal tables.

    This will be the database dump of the client's Drupal installation.
    Each migration project will have a specific dump file.
    """
    return ""
    
def get_migration_script():
    """Get standard migration SQL script.

    The standard migration script may not work on all Drupal configurations.
    """
    return "/sql/migration_standard.sql"