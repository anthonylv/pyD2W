#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Set up a Drupal to WordPress migration.
"""

import sys, getopt, os
import display_cli as cli
import settings as settings
from os.path import expanduser

def print_usage():
    """Print usage instructions to the screen.

    For the usage format, see http://en.wikipedia.org/wiki/Usage_message.
    """
    print """\
    Usage: d2wprojectsetup.py [-h --help | -p=path]

    Options:
    -p path, --path path
        Path to the project

    -h, --help
        Display options
    """    

def run_setup(path):
    """Setup the project.

    Args:
        path: Path to the project location.
    """
    print "The process will create new directories in "+path
    answer = cli.query_yes_no("Are you sure you want to continue?", "no")
    if answer:
        create_directory(path)
        create_directory(os.path.join(path, "Analysis"))
        create_directory(os.path.join(path, "Archives"))
        create_directory(os.path.join(path, "Exports"))
        create_directory(os.path.join(path, "Specifications"))
        create_directory(os.path.join(path, "SQL"))
        create_directory(os.path.join(path, "Testing"))
    else:
        print "Project setup aborted"
        

def get_default_project_path():
    """Gets the default project path.

    Returns:
        Path to the project directory
    """    
    project_path = os.getcwd()+os.sep+"new_project"
    try:
        project_path = settings.get_default_project_path()
    except AttributeError:
        print "Settings file does not have a default project path."
        print "Using default: {}".format(project_path)
    return project_path
    

def create_directory(path):
    """Create a directory.
    
    Args:
        path: Path to the project location.    
    """
    print "Creating directory: {}...".format(path)
    if not os.path.exists(path):
        try:
            os.makedirs(path)
            print "...done"
        except OSError as e:
            print "Sorry there was a problem creating the directory: {}".format(e.strerror)            
            if not path:
                print "The path string is empty"
    else:
        print "The directory {} already exists".format(path)
        

def process_arguments(options):
    """Process the command line options.

    Args:
        arguments (dictionary): A dictionary of options.
    """
    # Has the user specified a path?
    try:
        run_setup(options['path'])
    except KeyError:
        print "Aborting: No project path specified"


def main(argv):
    """Process the user's commands.

    Args:
        argv: The command line options.
    """
    try:
        opts, args = getopt.getopt(
            argv,
            "p:h",
            ["path=", "help"]
        )
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)

    arguments = dict()
    # Get command line options and arguments
    if len(opts) != 0:
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print_usage()
                sys.exit()
            elif opt in ("-p", "--path"):
                arguments['path'] = arg
    else:
        arguments['path'] = get_default_project_path()

    process_arguments(arguments)


# Program entry point
if __name__ == "__main__":
    main(sys.argv[1:])
