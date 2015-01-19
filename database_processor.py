#!/usr/bin/python

# Create unique term names by appending tid (term id)
def process_duplicate_term_names(drupal_terms_with_duplicate_names):
    updated_terms = list()
    duplicate_terms_count = len(drupal_terms_with_duplicate_names)
    if duplicate_terms_count > 0:
    	for term in drupal_terms_with_duplicate_names:
    	    term_attributes_list = {'tid': term["tid"], 'name': term["name"]+"_"+str(term["tid"])}
            updated_terms.append(term_attributes_list)
    return updated_terms
