#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Provide an interface to the Drupal 6 CMS database.

This module provides a wrapper to interfacing with the
content management system database.
Supports Drupal 6 only.
"""
import MySQLdb as mdb
import logging
import os, subprocess
from phpserialize import unserialize
#import subprocess
# Ensures cursors are closed upon completion of with block
# See discussion at
# http://stackoverflow.com/questions/5669878/python-mysqldb-when-to-close-cursors
from contextlib import closing
"""
***** Raising exceptions on warnings *****
* Migration stages often rely on a the successful completion of a 
* previous stage. Warnings may mean that data was not correctly
* prepared for a subsequent stage. In most cases, you want to
* raise an exception on warnings so you can investigate the problem.
"""
from warnings import filterwarnings
# Uncomment to suppress all warnings
#warnings.filterwarnings('ignore', category = mdb.Warning)
# Uncomment to raise exceptions on warnings
filterwarnings('error', category = mdb.Warning)


class Database:
    """Class to handle interaction with the Drupal database

    This class models the necessary interactions with the Drupal MySQL
    database to perform the migration.
    """
    _logger = None
    _db_connection = None
    _db_cur = None
    _host = ""
    _user = ""
    _password = ""
    _database = ""


    def __init__(self, host, user, password, database=None):
        self._logger = logging.getLogger(__name__)
        self._host = str(host)
        self._user = str(user)
        self._password = str(password)
        if database:
            self._database = str(database)
        self.open(host, user, password, database)


    def open(self, host, user, password, database=None):
        try:
            if database:
                self._db_connection = mdb.connect(
                    host,
                    user,
                    password,
                    database,
                    charset='utf8',
                    use_unicode=True
                )
            else:
                self._db_connection = mdb.connect(
                    host,
                    user,
                    password,
                    charset='utf8',
                    use_unicode=True
                )
        except mdb.OperationalError, ex:
            self._logger.error(
                "OperationalError on the database: %s",
                ex[1]
            )
            raise ex
        except mdb.Error, ex:
            self._logger.error(
                "Sorry there was an error %s: %s",
                ex[0],
                ex[1]
            )
            raise ex


    def close(self):
        if self._db_connection:
            self._db_connection.close()


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
                #print "Check database for problems {}: {}".format(e[0], e[1])
                self._logger.error(
                    "There was a problem while trying to run a query:\n\t%s",
                    e[1]
                )
                cur.close()
                raise
            except mdb.Warning, warn:
                self._logger.warning("%s", warn)
                raise
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
            self._logger.error(
                "Sorry there was an error %s: %s",
                e[0],
                e[1]
            )
            self._logger.error("Unable to insert data; rollback called")
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
            self._logger.warning(
                "Warning: expected only one %s table. Found %s",
                table,
                count
            )
        return count
        

    def get_drupal_version(self):
        """Get the Drupal installation version.
        """
        version = None
        result = None
        try:
            # Returns a tuple of dictionary objects
            result = self.query("SELECT info FROM system WHERE name='system'")
        except mdb.ProgrammingError as ex:
            self._logger.error(
                "Couldn't get the version number. "
                "Perhaps your system table is missing."
            )
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
        result = None
        try:
            # Returns a tuple of dictionary objects
            result = self.query(
                "SELECT value FROM variable WHERE name='site_name';"
            )
        except mdb.ProgrammingError as ex:
            self._logger.error(
                "Couldn't get site name. "
                "Perhaps your variable table is missing."
            )           
        # We expect the 'value' dictionary object as the first item
        if result:
            variable_row = result[0]
            variable_info = variable_row['value']
            # The variable info in Drupal is stored as a serialized string
            try:
                sitename = unserialize(variable_info.encode('utf8'))
            except Exception as ex:
                self._logger.error(
                    "Could not unserialize site name. Unknonw encoding?"
                )
                sitename = variable_info
                raise
        return sitename


    def get_drupal_posts(self):
        """Get all the nodes from the Drupal installation.
        """
        posts = None
        try:
            posts = self.query(
                "SELECT DISTINCT "
                "nid, FROM_UNIXTIME(created) post_date, title, type "
                "FROM node"
            )
        except mdb.ProgrammingError as ex:
            self._logger.error(
                "Couldn't get posts. Perhaps your node table is missing."
            )
        if not posts:
            posts = ()
        return posts


    def get_drupal_terms(self):
        """Get all the terms from the Drupal installation.
        """
        terms = None
        try:
            terms = self.query(
                "SELECT DISTINCT "
                "tid, name, REPLACE(LOWER(name), ' ', '_') slug, 0 "
                "FROM term_data WHERE (1);"
            )
        except mdb.ProgrammingError as ex:
            self._logger.error(
                "Couldn't get terms. "
                "Perhaps your term_data table is missing."
            )
        if not terms:
            terms = ()
        return terms


    def get_drupal_node_types(self):
        """Get the node types configured on the Drupal installation.
        """
        node_types = None
        try:
            node_types = self.query(
                "SELECT DISTINCT type, name, description FROM node_type n "
            )
        except mdb.ProgrammingError as ex:
            self._logger.error(
                "Couldn't get node types. "
                "Perhaps your node_type table is missing."
            )
        if not node_types:
            node_types = ()
        return node_types


    def get_drupal_node_count_by_type(self):
        """Get the number of nodes for each Drupal content type."""

        node_count = None
        try:
            node_count = self.query(
                "SELECT node_type.type, node_type.name, COUNT(node.nid) "
                "AS node_count "
                "FROM node "
                "INNER JOIN node_type ON node.type = node_type.type "
                "GROUP BY node_type.type;"
            )
        except mdb.ProgrammingError as ex:
            self._logger.error(
                "Couldn't get node count. "
                "Perhaps your node table is missing."
            )
        if not node_count:
            node_count = ()
        return node_count


    def get_drupal_duplicate_term_names(self):
        """Get any duplicate term names.

        We can't import duplicate terms into the WordPress wp_terms table
        Get aggregate of terms with duplicate names; we don't want each
        individual term entry with a duplicate name
        """
        term_names = None
        try:
            term_names = self.query(
                "SELECT tid, name, COUNT(*) c "
                "FROM term_data GROUP BY name HAVING c > 1"
            )
        except mdb.ProgrammingError as ex:
            self._logger.error(
                "Couldn't get term names. "
                "Perhaps your term_data table is missing."
            )
        if not term_names:
            term_names = ()
        return term_names


    def get_drupal_duplicate_terms(self):
        """Get each individual term that has a duplicate.

        This is different from get_drupal_duplicate_term_names() because
        it gets the aggregate of terms with duplicate names.
        """
        self._logger.debug("Getting duplicate terms...")
        duplicate_terms = None
        try:
            duplicate_terms = self.query(
                "SELECT term_data.tid, term_data.name "
                "FROM term_data "
                "INNER JOIN ( SELECT name FROM term_data "
                "GROUP BY name HAVING COUNT(name) >1 ) temp "
                "ON term_data.name=temp.name"
            )
        except mdb.ProgrammingError as ex:
            self._logger.error(
                "Couldn't get dupolicate terms. "
                "Perhaps your term_data table is missing."
            )
        if not duplicate_terms:
            duplicate_terms = ()
        return duplicate_terms


    def get_terms_exceeded_charlength(self):
        """Get any terms that exceed WordPress' character length.

        WordPress term name field is set 200 chars but Drupal's 
        term name is 255 chars.
        """
        terms = None
        try:
            terms = self.query(
                "SELECT tid, name "
                "FROM term_data WHERE CHAR_LENGTH(name) > 200;"
            )
        except mdb.ProgrammingError as ex:
            self._logger.error(
                "Couldn't get terms. "
                "Perhaps your term_data table is missing."
            )
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

        If there are multiple Drupal aliases with the same node ID, we will
        end up trying to create multiple entries into the WordPress wp_posts
        table with the same wp_posts ID. This will cause integrity constraint
        violation errors since wp_posts ID is a unique primary key.

        To avoid this error, we need to check for duplicate aliases
        """
        aliases = None
        try:
            aliases = self.query(
                "SELECT pid, src, COUNT(*) c "
                "FROM url_alias GROUP BY src HAVING c > 1;"
            )
        except mdb.ProgrammingError as ex:
            self._logger.error(
                "Couldn't get aliases. "
                "Perhaps your url_aliases table is missing."
            )
        if not aliases:
            aliases = ()
        return aliases
        

    def execute_sql_file(self, sql_file, database=None):
        """Use mysql on the command line to execute a MySQL file.

        This will produce a warning about using the password on the
        command line being insecure.
        """
        success = False
        try:
            self._logger.debug("Executing SQL file %s...", sql_file)

            user = str(self._user)
            password = str(self._password)
            
            if database is None:
                # Support connections where database has yet to be created
                process = subprocess.Popen(
                    ["mysql",
                    "-u"+ user,
                    "-p"+ password
                    ],
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                database = str(database)
                process = subprocess.Popen(
                    ["mysql",
                    "-u"+ user,
                    "-p"+ password,
                    database
                    ],
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
            out, err = process.communicate(file(sql_file).read())
            
            if process.returncode == 0:
                self._logger.debug("...done")
                success = True
            elif process.returncode == 1:
                self._logger.info(
                    "There were problems with executing the script:\n\n%s",
                    err
                )
            else:
                assert process.returncode > 1
                self._logger.error(
                    "Error while executing the script: %s", error
                )
        except IOError:
            self._logger.error("...could not find file. Aborting.")
        except Exception as ex:
            template = "A {0} exception occured:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            raise
        return success


    def __del__(self):
        if self._db_connection:
            self._db_connection.close()
