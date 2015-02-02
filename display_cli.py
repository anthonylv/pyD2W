#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Output pyD2W results to the command line.

This module handles display of pyD2W results to the command line.
"""

import sys
from prettytable import PrettyTable


def print_diagnostics(diagnostic_results):
    """Print the diagnostic results to the command line.
    
    Args:
        diagnostic_results (dictionary): A dictionary containing the results.
    """
    drupal_posts_count = diagnostic_results["posts_count"]
    drupal_terms_count = diagnostic_results["terms_count"]
    drupal_duplicate_terms_count = diagnostic_results["duplicate_terms_count"]
    drupal_node_types_count = diagnostic_results["node_types_count"]
    drupal_terms_exceeded_char_count = diagnostic_results["terms_exceeded_char_count"]
    drupal_duplicate_aliases_count = diagnostic_results["duplicate_aliases_count"]
    drupal_node_count_by_type = diagnostic_results["node_count_by_type"]
    drupal_node_types = diagnostic_results["node_types"]    

    print "\n=================================================="
    print "Starting Drupal To WordPress diagnostics"
    print "==================================================\n"
    
    # Print Properties Table
    table_properties = PrettyTable(["Property", "Found in Drupal"])
    table_properties.align["Property"] = "l"
    table_properties.align["Found in Drupal"] = "l"
    table_properties.add_row(["Terms", "There are {} terms".format(drupal_terms_count)] )
    table_properties.add_row( ["Node types", "There are {} node types".format(drupal_node_types_count)] )
    table_properties.add_row( ["Post entries", "There are {} post entries".format(drupal_posts_count)] )
    table_properties.add_row( ["Duplicate terms", "There are {} duplicate terms".format(drupal_duplicate_terms_count)] )    
    table_properties.add_row( ["Term character length exceeded", "{} terms exceed WordPress' 200 character length".format(drupal_terms_exceeded_char_count)] )
    table_properties.add_row( ["Duplicate aliases", "{} duplicate aliases found".format(drupal_duplicate_aliases_count)] )    
    print table_properties
    
    # Print Node Types Table
    types_list = list(types["type"] for types in drupal_node_types)
    types_string = ", ".join(types_list)
    
    table_node_types = PrettyTable(["Node type"])
    table_node_types.align["Node type"] = "l"
    for row in drupal_node_types:
        table_node_types.add_row([row["type"]])    
    print table_node_types
    
    # Print Node count by content type table
    table_node_count_by_type = PrettyTable(["Node type", "Name", "Count"])
    table_node_count_by_type.align["Node type"] = "l"
    table_node_count_by_type.align["Name"] = "l"
    table_node_count_by_type.align["Count"] = "l"        
    for row in drupal_node_count_by_type:
        table_node_count_by_type.add_row([row["type"], row["name"], row["node_count"]])
    print table_node_count_by_type


def print_usage():
    """Print usage instructions to the screen.
    
    For the usage format, see http://en.wikipedia.org/wiki/Usage_message.
    """
    print """\
Usage: drupaltowordpress.py [-h --help | -a=analyse|fix|reset|sqlscript] [-d=database_name] [-s=script_path]

Options:
-a act, --action act
    Perform an action on the database (see Actions section below)
    
-d database_name, --database database_name
    Perform the action on database specified by database_name

-s script_path, --sqlscript script_path
    Run a MySQL script file specified by script_path

-h, --help
    Display options

Actions:
analyse     : Analyse the Drupal database
fix         : Try to fix database problems
reset       : Reset the tables into a clean state ready for another migration pass

"""


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.
    
    Args:
        question (string): is a string that is presented to the user.
        default (string): is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    
    This code is a recipe from http://code.activestate.com/recipes/577058/.
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")
