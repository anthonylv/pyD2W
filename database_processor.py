#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Make the Drupal database entries compatible with WordPress.

This module contains the logic needed to convert Drupal data so that it can
be inserted into a WordPress database without causing errors.
"""


def process_duplicate_term_names(drupal_terms_with_duplicate_names):
    """Create unique term names by appending the term id.
    
    Args:
        drupal_terms_with_duplicate_names (list): A list of Drupal terms.
        
    Returns:
        updated_terms (list): A list of Drupal terms comaptible with WordPress.
    """
    updated_terms = list()
    duplicate_terms_count = len(drupal_terms_with_duplicate_names)
    if duplicate_terms_count > 0:
    	for term in drupal_terms_with_duplicate_names:
    	    term_attributes_list = {'tid': term["tid"], 'name': term["name"]+"_"+str(term["tid"])}
            updated_terms.append(term_attributes_list)
    return updated_terms
