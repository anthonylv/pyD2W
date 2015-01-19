#!/usr/bin/python
import sys, getopt, os
import display_cli as cli
import database_processor as processor
import settings
from database_interface import Database

def run_diagnostics():
    database = Database(
        settings.get_drupal_host(),
        settings.get_drupal_username(),
        settings.get_drupal_password(),
        settings.get_drupal_database()
    )
    if database.connected():
        # General analysis of Drupal database properties
        drupal_posts = database.get_drupal_posts()
        drupal_terms = database.get_drupal_terms()
        drupal_node_types = database.get_drupal_node_types()
        
        # Look for common problems
        drupal_duplicate_terms = database.get_drupal_duplicate_term_names()
        drupal_terms_exceeded_charlength = database.get_terms_exceeded_charlength()
        drupal_dupliate_alias = database.get_dupliate_alias()
        
        results = {
            "posts": drupal_posts,
            "terms": drupal_posts,
            "duplicate_terms": drupal_duplicate_terms,
            "node_types": drupal_node_types,
            "terms_exceeded_charlength": drupal_terms_exceeded_charlength,
            "dupliate_alias": drupal_dupliate_alias
        }
        cli.print_diagnostics(results)
    else:
        print "No database connection"


# Reset the tables into a clean state ready for another migration pass
def reset():
    wp_tables_setup_success = False
    database = Database(
        settings.get_drupal_host(),
        settings.get_drupal_username(),
        settings.get_drupal_password(),
        settings.get_drupal_database()
    )
    if database.connected():
        database.cleanup_tables()
        wordpress_setup_file = os.path.dirname(os.path.realpath(__file__))+settings.get_wordpress_setup_sql_script_filename()
        if os.path.isfile(wordpress_setup_file):
            wp_tables_setup_success = database.execute_sql_file(wordpress_setup_file)
        else:
            print "Could not find a SQL script file to setup the WordPress tables"
    else:
        print "No database connection"
    if wp_tables_setup_success:
        print "WordPress export tables were created"
    else:
        print "Could not create WordPress export tables"

def run_fix():
    print "This process will alter your database"
    answer = cli.query_yes_no("Are you sure you want to continue?", "no")
    if answer:
        database = Database(
            settings.get_drupal_host(),
            settings.get_drupal_username(),
            settings.get_drupal_password(),
            settings.get_drupal_database()
        )
        if database.connected():
            drupal_terms_with_duplicate_names = database.get_drupal_terms_with_duplicate_names()
            fixed_term_names = processor.process_duplicate_term_names(drupal_terms_with_duplicate_names)
            
            for term in fixed_term_names:
                result = database.insert_processed_term_names(term["tid"], term["name"])
	            #pass
                #print "[{}] : {}".format(term["tid"], term["name"])
                # TO DO:
                # Compare drupal_terms_with_duplicate_names with fixed_term_names
                # Ensure tid are same                
        else:
            print "No database connection"
    else:
        print "Fix process aborted"
        
        
def main(argv):
    try:
      opts, args = getopt.getopt(argv,"dfhr",["fix", "help", "diagnostic", "reset"])
    except getopt.GetoptError:
      cli.print_usage()
      sys.exit(2)
      
    if len(opts) == 0:
        cli.print_usage()
    else:
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                cli.print_usage()
                sys.exit()
            elif opt in ("-d", "--diagnostic"):
                run_diagnostics()
            elif opt in ("-f", "--fix"):
                run_fix()
            elif opt in ("-r", "--reset"):
                reset()
                
    
if __name__ == "__main__":
   main(sys.argv[1:])
