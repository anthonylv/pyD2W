#!/usr/bin/python
import MySQLdb as mdb
# Ensures cursors are closed upon completion of with block
# See discussion at http://stackoverflow.com/questions/5669878/python-mysqldb-when-to-close-cursors
from contextlib import closing


class Database:
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
            # self._db_cur = self._db_connection.cursor(mdb.cursors.DictCursor)
            # Try opening a normal cursor to get rollbacks
            # self._db_cur = self._db_connection.cursor()
        except:
            print "Unable to connect to database"
        

    def connected(self):
        connection_status = False
        if self._db_connection:
            connection_status = True
        return connection_status 
    

    def query(self, query, params=None):
        results = None
        '''
        try:
            self._db_cur = self._db_connection.cursor(mdb.cursors.DictCursor)
            self._db_cur.execute(query)
            results = self._db_cur.fetchall()            
        except:
            print "Error: unable to fetch data"
        return results
        '''
        with closing(self._db_connection.cursor(mdb.cursors.DictCursor)) as cur:
            cur.execute(query)
            results = cur.fetchall()
        return results
        

    def insert(self, query, params=None):
        results = None
        try:
            cur = self._db_connection.cursor()
            cur.execute(query)
            self._db_connection.commit()
        except mdb.Error,e:
            print "Error {}: {}".format(e[0],e[1])
            print "Unable to insert data; rollback called"
            self._db_connection.rollback()
            cur.close()
        return results
                
        
    def get_drupal_posts(self):
        return self.query("SELECT DISTINCT nid, FROM_UNIXTIME(created) post_date, title, type FROM node")
        
        
    def get_drupal_terms(self):
        return self.query("SELECT DISTINCT tid, name, REPLACE(LOWER(name), ' ', '_') slug, 0 FROM term_data WHERE (1);")

    
    def get_drupal_node_types(self):
        return self.query("SELECT DISTINCT type, name, description FROM node_type n ")

      
    # We can't import duplicate terms into the WordPress wp_terms table
    # Get aggregate of terms with duplicate names; we don't want each individual term
    # entry with a duplicate name
    def get_drupal_duplicate_term_names(self):
        return self.query("SELECT tid, name, COUNT(*) c FROM term_data GROUP BY name HAVING c > 1")


    # Get each individual term that has a duplicate; different from the aggregate of terms with duplicate names
    def get_drupal_terms_with_duplicate_names(self):
        return self.query("SELECT term_data.tid, term_data.name FROM term_data INNER JOIN ( SELECT name FROM term_data GROUP BY name HAVING COUNT(name) >1 ) temp ON term_data.name=temp.name")
 

    # WordPress term name field is set 200 chars but Drupal's is term name is 255 chars
    def get_terms_exceeded_charlength(self):
        return self.query("SELECT tid, name FROM term_data WHERE CHAR_LENGTH(name) > 200;")
        
    
    # The node ID in Drupal's node table is used to create the post ID in WordPress' wp_posts table.
    #
    # The post name in WordPress' wp_posts table is created using either
    #   (a) the url alias (dst field) in Drupal's url_alias table OR
    #   (b) the node id (nid) in Drupal's node table IF there is no url alias
    #
    # If there are multiple Drupal aliases with the same node ID, we will end up trying to create multiple entries
    # into the WordPress wp_posts table with the same wp_posts ID. This will cause integrity constraint violation
    # errors since wp_posts ID is a unique primary key.
    #
    # To avoid this error, we need to check for duplicate aliases
    def get_dupliate_alias(self):
        return self.query("SELECT pid, src, COUNT(*) c FROM url_alias GROUP BY src HAVING c > 1;")
        
    
    def insert_fixed_term_names(self):
        self.query("CREATE TABLE IF NOT EXISTS acc_fixed_term_names ( tid INT(10) NOT NULL UNIQUE, name VARCHAR(255)) ENGINE=INNODB;")
        self.insert("INSERT INTO acc_fixed_term_names (tid, name) VALUES (938, 'test name 01');")

        
    def __del__(self):
        if self._db_connection:
            self._db_connection.close()
