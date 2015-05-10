#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Provide an interface to the CMS database.

This module provides a wrapper to interfacing with the content management system database.
"""
import MySQLdb as mdb
import os
from phpserialize import unserialize
#import subprocess
# Ensures cursors are closed upon completion of with block
# See discussion at http://stackoverflow.com/questions/5669878/python-mysqldb-when-to-close-cursors
from contextlib import closing
# Suppress warnings for tables that have not been created
import warnings
warnings.filterwarnings("ignore", "Unknown table.*")
# Uncomment to suppress all warnings
#warnings.simplefilter("ignore")

class Database:
    """Class to handle interaction with the Drupal database

    This class models the necessary interactions with the Drupal MySQL
    database to perform the migration.
    """
    _db_connection = None
    _db_cur = None
    _host = ""
    _user = ""
    _password = ""
    _database = ""


    def __init__(self, host, user, password, database):
        self._host = host
        self._user = user
        self._password = password
        self._database = database

        try:
            self._db_connection = mdb.connect(host, user, password, database)
        except:
            print "Unable to connect to database"


    def connected(self):
        """Check if there is an open database connection.

        Returns:
            boolean: True if there is an open database connection, False otherwise.
        """
        connection_status = False
        if self._db_connection:
            connection_status = True
        return connection_status
        
    def get_database(self):
        """Check if the selected database.

        Returns:
            string: Database name.
        """        
        return self._database


    def query(self, query, params=None):
        """Run a MySQL query string.

        Args:
            query (string): MySQL query string.

        Returns:
            results: Results of the query as a list of tuples.
        """
        results = None
        with closing(self._db_connection.cursor(mdb.cursors.DictCursor)) as cur:
            try:
                cur.execute(query)
                results = cur.fetchall()
            except (mdb.OperationalError, mdb.ProgrammingError), e:
                # Uncomment to show error number
                # print "Check database for problems {}: {}".format(e[0], e[1])
                print "Check database for problems: {}".format(e[1])
                cur.close()
        return results


    def insert(self, query, params=None):
        """Run a MySQL INSERT query string.

        Args:
            query (string): MySQL query string.

        Returns:
            results: Results of the query.
        """
        # Assume success unless an exception is raised
        success = True
        try:
            cur = self._db_connection.cursor()
            cur.execute(query)
            self._db_connection.commit()
        except mdb.Error, e:
            success = False
            print "Sorry there was an error {}: {}".format(e[0], e[1])
            print "Unable to insert data; rollback called"
            self._db_connection.rollback()
            cur.close()
        return success


    def get_table_count(self, table):
        """Query to check if the table exists in the database.

        Args:
            table (string): The Drupal table to check.

        Returns:
            long: table count
        """
        count = 0
        query = "SELECT count(*) FROM information_schema.tables \
                WHERE table_schema = '{0}' AND table_name = '{1}' LIMIT 1;".format(
                    self._database,
                    table
                    )

        result = self.query(query)
        dict_item = result[0]
        count = dict_item['count(*)']
        if (count > 1 ):
            print "Warning: expected only one {0} table. Found {1}".format(table, count)
        return count
        

    def get_drupal_version(self):
        """Get the Drupal installation version.
        """
        version = "[Unknown version]"
        # Returns a tuple of dictionary objects
        result = self.query("SELECT info FROM system WHERE name='system'")
        if result:
            # We expect the 'info' dictionary object as the first item
            system_row = result[0]
            system_info = system_row['info']
            # The system info in Drupal is stored as a serialized string
            system_info_dict = unserialize(system_info)
            version = system_info_dict['version']
        return version


    def get_drupal_sitename(self):
        """Get the Drupal installation version.
        """
        sitename = "[Unknown sitename]"
        # Returns a tuple of dictionary objects
        
        result = self.query("SELECT value FROM variable WHERE name='site_name';")    
        # We expect the 'value' dictionary object as the first item
        if result:
            variable_row = result[0]
            variable_info = variable_row['value']
            # The variable info in Drupal is stored as a serialized string
            sitename = unserialize(variable_info)
        return sitename

    def get_drupal_posts(self):
        """Get all the nodes from the Drupal installation.
        """
        posts = self.query("SELECT DISTINCT nid, FROM_UNIXTIME(created) post_date, title, type \
                            FROM node")
        if not posts:
            posts = ()
        return posts


    def get_drupal_terms(self):
        """Get all the terms from the Drupal installation.
        """
        terms = self.query("SELECT DISTINCT tid, name, REPLACE(LOWER(name), ' ', '_') slug, 0 \
                            FROM term_data WHERE (1);")
        if not terms:
            terms = ()
        return terms


    def get_drupal_node_types(self):
        """Get the node types configured on the Drupal installation.
        """
        node_types = self.query("SELECT DISTINCT type, name, description FROM node_type n ")

        if not node_types:
            node_types = ()
        return node_types


    def get_drupal_node_count_by_type(self):
        """Get the number of nodes for each Drupal content type."""

        node_count = self.query(
            "SELECT node_type.type, node_type.name, COUNT(node.nid) AS node_count " \
                "FROM node " \
                "INNER JOIN node_type ON node.type = node_type.type " \
                "GROUP BY node_type.type;")
        if not node_count:
            node_count = ()
        return node_count


    def get_drupal_duplicate_term_names(self):
        """Get any duplicate term names.

        We can't import duplicate terms into the WordPress wp_terms table
        Get aggregate of terms with duplicate names; we don't want each individual term
        entry with a duplicate name
        """
        term_names = self.query(
            "SELECT tid, name, COUNT(*) c FROM term_data GROUP BY name HAVING c > 1"
        )
        if not term_names:
            term_names = ()
        return term_names


    def get_drupal_duplicate_terms(self):
        """Get each individual term that has a duplicate.

        This is different from get_drupal_duplicate_term_names() because
        it gets the aggregate of terms with duplicate names.
        """
        duplicate_terms = self.query("SELECT term_data.tid, term_data.name \
                            FROM term_data \
                            INNER JOIN ( SELECT name FROM term_data \
                            GROUP BY name HAVING COUNT(name) >1 ) temp \
                            ON term_data.name=temp.name")
        if not duplicate_terms:
            duplicate_terms = ()
        return duplicate_terms


    def get_terms_exceeded_charlength(self):
        """Get any terms that exceed WordPress' character length.

        WordPress term name field is set 200 chars but Drupal's is term name is 255 chars.
        """
        terms = self.query("SELECT tid, name FROM term_data WHERE CHAR_LENGTH(name) > 200;")
        if not terms:
            terms = ()
        return terms


    def get_duplicate_aliases(self):
        """Get any duplicate aliases.

        The node ID in Drupal's node table is used to create the post ID in
        WordPress' wp_posts table.

        The post name in WordPress' wp_posts table is created using either
          (a) the url alias (dst field) in Drupal's url_alias table OR
          (b) the node id (nid) in Drupal's node table IF there is no url alias

        If there are multiple Drupal aliases with the same node ID, we will end
        up trying to create multiple entries into the WordPress wp_posts table
        with the same wp_posts ID. This will cause integrity constraint violation
        errors since wp_posts ID is a unique primary key.

        To avoid this error, we need to check for duplicate aliases
        """
        aliases = self.query(
            "SELECT pid, src, COUNT(*) c FROM url_alias GROUP BY src HAVING c > 1;"
        )
        if not aliases:
            aliases = ()
        return aliases


    def uniquify_url_aliases(self):
        """Remove duplicate aliases but keep a copy in a working table.

        URL alias will be used as the WordPress post slug but these need to be unique.
        Create a url_alias table of unique aliases and keep a copy of the original
        for later processing.
        """
        self.query("DROP TABLE IF EXISTS acc_url_alias_dups_removed;")
        self.query("DROP TABLE IF EXISTS acc_url_alias_with_dups;")
        self.query("CREATE TABLE acc_url_alias_dups_removed \
                    AS SELECT pid, src, dst FROM url_alias GROUP BY src;")
        self.query("RENAME TABLE url_alias TO acc_url_alias_with_dups;")
        self.query("RENAME TABLE acc_url_alias_dups_removed TO url_alias;")


    def update_processed_term_name(self, tid, name):
        """Insert term names that have been processed to meet WordPress' criteria.

        Args:
            tid (integer): The Drupal taxonomy ID.
            name (string): The Drupal taxonomy name.
        """
        query = "UPDATE term_data SET name='"+name+"' WHERE tid="+str(tid)+";"
        return self.insert(query)


    def update_term_name_length(self):
        """Truncate term name to fit WordPress' 200 character limit
        """
        self.query("UPDATE term_data SET name=SUBSTRING(name, 1, 200);")


    def create_working_tables(self):
        """Create some working tables to hold temporary data.

        This function creates working tables useful for debugging migration problems.
        """
        self.query("CREATE TABLE IF NOT EXISTS acc_fixed_term_names ( \
                        tid INT(10) NOT NULL UNIQUE, name VARCHAR(255)) ENGINE=INNODB;")


    def cleanup_tables(self):
        """Cleanup working tables.

        We need to clean up working tables when running multiple migration passes.
        Execute as individual statements as MySQLdb doesn't seem to support
        multiple statement execution
        """
        # Temporary working tables
        # This will generate warnings if the tables don't exist so we suppress them with
        # warnings.filterwarnings upon import of Warnings module
        self.query("DROP TABLE IF EXISTS acc_duplicates;")
        self.query("DROP TABLE IF EXISTS acc_news_terms;")
        self.query("DROP TABLE IF EXISTS acc_tags_terms;")
        self.query("DROP TABLE IF EXISTS acc_wp_tags;")
        self.query("DROP TABLE IF EXISTS acc_wp_categories;")
        self.query("DROP TABLE IF EXISTS acc_users_post_count;")
        self.query("DROP TABLE IF EXISTS acc_users_comment_count;")
        self.query("DROP TABLE IF EXISTS acc_users_with_content;")
        self.query("DROP TABLE IF EXISTS acc_users_post_count;")
        self.query("DROP TABLE IF EXISTS acc_url_alias_dups_removed")
        self.query("DROP TABLE IF EXISTS acc_url_alias_with_dups;")
        # WordPress tables
        # Commented out because WordPress tables are now cleaned up
        # by importing the WordPress dump file
        #self.query("TRUNCATE TABLE acc_export_wp_comments;")
        #self.query("TRUNCATE TABLE acc_export_wp_links;")
        #self.query("TRUNCATE TABLE acc_export_wp_postmeta;")
        #self.query("TRUNCATE TABLE acc_export_wp_posts;")
        #self.query("TRUNCATE TABLE acc_export_wp_term_relationships;")
        #self.query("TRUNCATE TABLE acc_export_wp_term_taxonomy;")
        #self.query("TRUNCATE TABLE acc_export_wp_terms;")
        #self.query("TRUNCATE TABLE acc_export_wp_users;")
        # For some installations, we make changes to the wp_usermeta table
        # self.query("TRUNCATE TABLE acc_export_wp_usermeta;")


    def execute_sql_file(self, sql_file):
        """Use mysql on the command line to execute a MySQL file.

        This will produce a warning about using the password on the command line being insecure.
        I've not found a way to suppress the warning and Popen from subprocess module
        doesn't seem to work with running a mysql script.
        """
        success = False
        if os.path.isfile(sql_file):
            print "Executing SQL file..."
            command = "mysql -u"+self._user+" -p"+self._password+" "+self._database+" < "+sql_file
            result = os.system(command)
            if result != 0:
                print "Sorry, something went wrong when executing the SQL file. " \
                "Please check error messages"
            else:
                print "Script run complete"
                success = True
        else:
            print "Could not find a SQL file"
        return success

    def __del__(self):
        if self._db_connection:
            self._db_connection.close()
