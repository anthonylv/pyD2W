#!/usr/bin/python
import sys, getopt
import display_cli as cli
import database_fixer as fixer
import settings
from database_interface import Database


def run_diagnostics():
    database = Database(
        settings.getDrupalHost(),
        settings.getDrupalUsername(),
        settings.getDrupalPassword(),
        settings.getDrupalDatabase()
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
    

def run_fix():
    print "This process will alter your database"
    answer = cli.query_yes_no("Are you sure you want to continue?", "no")
    if answer:
        database = Database(
            settings.getDrupalHost(),
            settings.getDrupalUsername(),
            settings.getDrupalPassword(),
            settings.getDrupalDatabase()
        )
        if database.connected():
            drupal_terms_with_duplicate_names = database.get_drupal_terms_with_duplicate_names()
            fixed_term_names = fixer.fix_duplicate_term_names(drupal_terms_with_duplicate_names)
            
            
            result = database.insert_fixed_term_names()
            return result;
            

            for term in fixed_term_names:
                #print "[{}] : {}".format(term["tid"], term["name"])
                '''
                TO DO:
                Compare drupal_terms_with_duplicate_names with fixed_term_names
                Ensure tid are same
                
                '''
                
                
        else:
            print "No database connection"
    else:
        print "Fix process aborted"
        
        
def main(argv):
    try:
      opts, args = getopt.getopt(argv,"dfh",["fix", "help", "diagnostic"])
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
                
    
if __name__ == "__main__":
   main(sys.argv[1:])
