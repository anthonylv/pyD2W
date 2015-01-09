#!/usr/bin/python
import MySQLdb as mdb

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
        self._db_connection = mdb.connect(host, user, password, database)
        self._db_cur = self._db_connection.cursor(mdb.cursors.DictCursor)


    def query(self, query, params=None):
        try:
            self._db_cur.execute(query)
            results = self._db_cur.fetchall()            
        except:
            print "Error: unable to fetch data"
        return results
        
        
    def get_drupal_posts(self):
        return self.query("SELECT DISTINCT nid, FROM_UNIXTIME(created) post_date, title, type FROM node")
        
        
    def get_drupal_terms(self):
        return self.query("SELECT DISTINCT tid, name, REPLACE(LOWER(name), ' ', '_') slug, 0 FROM term_data WHERE (1);")

    
    def get_drupal_node_types(self):
        return self.query("SELECT DISTINCT type, name, description FROM node_type n ")

      
    # We can't import duplicate terms into the WordPress wp_terms table
    def get_drupal_duplicate_terms(self):
        return self.query("SELECT tid, name, COUNT(*) c FROM term_data GROUP BY name HAVING c > 1")
                

    # WordPress term name field is set 200 chars but Drupal's is term name is 255 chars
    def get_terms_exceeded_charlength(self):
        return self.query("SELECT tid, name FROM term_data WHERE CHAR_LENGTH(name) > 200;")
        
        
    '''
     * The node ID in Drupal's node table is used to create the post ID in WordPress' wp_posts table.
     *
     * The post name in WordPress' wp_posts table is created using either
     *   (a) the url alias (dst field) in Drupal's url_alias table OR
     *   (b) the node id (nid) in Drupal's node table IF there is no url alias
     *
     * If there are multiple Drupal aliases with the same node ID, we will end up trying to create multiple entries
     * into the WordPress wp_posts table with the same wp_posts ID. This will cause integrity constraint violation
     * errors since wp_posts ID is a unique primary key.
     *
     * To avoid this error, we need to check for duplicate aliases
     '''
    def get_dupliate_alias(self):
        return self.query("SELECT pid, src, COUNT(*) c FROM url_alias GROUP BY src HAVING c > 1;")

        
    def __del__(self):
        self._db_connection.close()
